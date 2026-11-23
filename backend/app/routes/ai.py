import json
import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from ..extensions import db
from ..models import (
    AIAnalysis,
    AIChatMessage,
    AIChatSession,
    AIPracticeQuestion,
    AssessmentAttempt,
    AssessmentSubjectResult,
    Question,
    User,
)
from ..question_bank import SUBJECTS
from ..services.ai_features import (
    SUBJECT_TIPS,
    fallback_analysis,
    fallback_chat_reply,
    validate_analysis_response,
    validate_practice_question,
)
from ..services.nemotron import NemotronClient, NemotronUnavailable

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


def _current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def _request_data():
    data = request.get_json(silent=True)
    if data is None:
        return {}
    return data if isinstance(data, dict) else None


def _iso_utc(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _scores_for_attempt(attempt):
    return [
        {
            "subject": row.subject,
            "correct_answers": row.correct_answers,
            "total_questions": row.total_questions,
            "score_percent": row.score_percent,
            "insight": row.insight,
        }
        for row in AssessmentSubjectResult.query.filter_by(attempt_id=attempt.id).order_by(AssessmentSubjectResult.subject).all()
    ]


def _attempt_metrics(user, attempt):
    """Build chart and comparison metrics exclusively from saved attempt rows."""
    from ..models import AssessmentAnswer, AssessmentAttemptQuestion
    rows = (db.session.query(AssessmentAttemptQuestion, Question, AssessmentAnswer)
        .join(Question, Question.id == AssessmentAttemptQuestion.question_id)
        .outerjoin(AssessmentAnswer, (AssessmentAnswer.attempt_id == attempt.id) & (AssessmentAnswer.question_id == Question.id))
        .filter(AssessmentAttemptQuestion.attempt_id == attempt.id).order_by(AssessmentAttemptQuestion.position).all())
    topics, difficulties, timing = {}, {}, []
    for member, question, answer in rows:
        topic = topics.setdefault(question.topic, {"correct": 0, "total": 0})
        topic["total"] += 1
        topic["correct"] += int(bool(answer and answer.is_correct))
        difficulty = difficulties.setdefault(question.difficulty, {"correct": 0, "total": 0})
        difficulty["total"] += 1
        difficulty["correct"] += int(bool(answer and answer.is_correct))
        if answer and answer.time_spent_seconds is not None:
            timing.append({"question": member.position + 1, "seconds": answer.time_spent_seconds, "correct": bool(answer.is_correct)})
    topic_rows = [{"topic": name, "correct": data["correct"], "total": data["total"],
                   "accuracy": round(data["correct"] * 100 / data["total"], 1)} for name, data in sorted(topics.items())]
    difficulty_rows = [{"difficulty": name.title(), "correct": data["correct"], "total": data["total"],
                        "accuracy": round(data["correct"] * 100 / data["total"], 1)} for name, data in sorted(difficulties.items())]
    previous = (AssessmentAttempt.query.filter_by(user_id=user.id, assessment_mode="ai", assessment_category=attempt.assessment_category)
        .filter(AssessmentAttempt.completed_at.isnot(None), AssessmentAttempt.id != attempt.id)
        .filter(AssessmentAttempt.completed_at < attempt.completed_at).order_by(AssessmentAttempt.completed_at.desc()).first())
    history_rows = (AssessmentAttempt.query.filter_by(user_id=user.id, assessment_mode="ai", assessment_category=attempt.assessment_category)
        .filter(AssessmentAttempt.completed_at.isnot(None)).order_by(AssessmentAttempt.completed_at.asc()).all())
    return {"overall": {"correct": attempt.correct_answers, "incorrect": max(0, attempt.total_questions - attempt.correct_answers),
                         "total": attempt.total_questions, "accuracy": attempt.score_percent},
        "subjects": _scores_for_attempt(attempt), "topics": topic_rows,
        "strengths": [row["topic"] for row in topic_rows if row["accuracy"] >= 70],
        "weaknesses": [row["topic"] for row in topic_rows if row["accuracy"] < 50],
        "difficulties": difficulty_rows, "time_vs_accuracy": timing,
        "history": [{"date": row.completed_at.date().isoformat(), "accuracy": row.score_percent} for row in history_rows],
        "previous_attempt": ({"attempt_id": previous.id, "accuracy": previous.score_percent,
                              "change": round(attempt.score_percent - previous.score_percent, 1)} if previous else None)}


def _recent_performance(user, limit=5):
    attempts = (
        AssessmentAttempt.query.filter_by(user_id=user.id)
        .filter(AssessmentAttempt.completed_at.isnot(None))
        .order_by(AssessmentAttempt.completed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "attempt_id": attempt.id,
            "completed_at": _iso_utc(attempt.completed_at),
            "overall_score_percent": attempt.score_percent,
            "correct_answers": attempt.correct_answers,
            "total_questions": attempt.total_questions,
            "subjects": _scores_for_attempt(attempt),
        }
        for attempt in attempts
    ]


def _external_performance(history):
    """Share coarse, de-identified performance bands rather than exact student scores."""
    return [
        {
            "overall_performance": _performance_band(item["overall_score_percent"]),
            "subjects": [
                {"subject": row["subject"], "performance": row["insight"]}
                for row in item["subjects"]
            ],
        }
        for item in history
    ]


def _performance_band(score):
    if score >= 70:
        return "Strength"
    if score < 50:
        return "Needs focus"
    return "Developing"


def _redact_contact_details(text):
    text = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[email removed]", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\w)(?:\+?\d[\s().-]*){9,15}(?!\w)", "[number removed]", text)
    return re.sub(r"\b(?:sk-or-v1|sk-[A-Za-z0-9_-]{8,})[A-Za-z0-9_-]*\b", "[secret removed]", text, flags=re.IGNORECASE)


def _analysis_dict(row):
    return {
        "id": row.id,
        "attempt_id": row.attempt_id,
        "created_at": _iso_utc(row.created_at),
        "source": row.source,
        "content": row.content,
    }


def _fallback_roadmap_prompt(profile, performances, history, verified_metrics=None):
    system = (
        "You are a placement preparation coach. Use only the supplied placement goal and recorded assessment results. "
        "Do not invent, change, or estimate any score, event, qualification, target job, or student detail. "
        "Do not calculate or restate numeric scores; the application displays those directly from its database. "
        "Return exactly one JSON object with keys summary, subject_advice, roadmap. "
        "subject_advice must contain one object for each supplied subject with keys subject, guidance, activities. "
        "roadmap must have exactly four objects with keys week (1-4), focus, activities. "
        "Give actionable, supportive study guidance and align priorities with the actual subject scores."
    )
    context = {"student_profile": profile, "selected_assessment_subjects": performances, "recent_assessment_history": history,
               "verified_topic_difficulty_and_timing_metrics": verified_metrics}
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "Create a personalized skill-gap analysis and four-week placement preparation roadmap from this data:\n" + json.dumps(context, ensure_ascii=False)},
    ]


@ai_bp.get("/analysis")
def get_analyses():
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    rows = AIAnalysis.query.filter_by(user_id=user.id).order_by(AIAnalysis.created_at.desc()).limit(20).all()
    return jsonify(analyses=[_analysis_dict(row) for row in rows])


@ai_bp.post("/analysis")
def create_analysis():
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    data = _request_data()
    if data is None:
        return jsonify(error="Request body must be a JSON object."), 400
    requested_id = data.get("attempt_id")
    if requested_id is not None and (isinstance(requested_id, bool) or not isinstance(requested_id, int)):
        return jsonify(error="Assessment ID must be an integer."), 400
    query = AssessmentAttempt.query.filter_by(user_id=user.id).filter(AssessmentAttempt.completed_at.isnot(None))
    attempt = query.filter_by(id=requested_id).first() if requested_id is not None else query.order_by(AssessmentAttempt.completed_at.desc()).first()
    if not attempt:
        return jsonify(error="Complete an assessment before requesting a personalized analysis."), 404
    performances = _scores_for_attempt(attempt)
    if not performances:
        return jsonify(error="This assessment has no stored subject results."), 409

    metrics = _attempt_metrics(user, attempt) if attempt.assessment_mode == "ai" else None
    profile_context = {"goal": "placement preparation"}
    if metrics:
        from ..models import StudentProfile
        student_profile = StudentProfile.query.filter_by(user_id=user.id).first()
        if student_profile:
            profile_context.update({"degree": student_profile.degree, "department": student_profile.department,
                "target_roles": student_profile.target_roles or [], "preferred_language": student_profile.preferred_language})
    source = "nemotron"
    try:
        response = NemotronClient().complete_json(
            _fallback_roadmap_prompt(
                profile_context,
                _external_performance([{
                    "overall_score_percent": attempt.score_percent,
                    "subjects": performances,
                }]),
                _external_performance(_recent_performance(user)),
                metrics,
            ),
            max_tokens=1800,
        )
        content = validate_analysis_response(response, performances)
    except (NemotronUnavailable, ValueError, TypeError):
        source = "fallback"
        content = fallback_analysis(performances, attempt.score_percent, attempt.correct_answers, attempt.total_questions)

    if metrics:
        content["metrics"] = metrics
        weak = metrics["weaknesses"] or [row["topic"] for row in metrics["topics"][:3]]
        focus = weak[0] if weak else "Review your assessment answers"
        content["seven_day_roadmap"] = [
            {"day": day, "focus": weak[(day - 1) % len(weak)] if weak else focus,
             "activity": (f"Review core concepts and worked examples in {weak[(day - 1) % len(weak)]}." if weak else "Review every missed question and its explanation.")}
            for day in range(1, 8)
        ]

    row = AIAnalysis(user_id=user.id, attempt_id=attempt.id, content=content, source=source)
    db.session.add(row)
    db.session.commit()
    return jsonify(analysis=_analysis_dict(row)), 201


@ai_bp.get("/chat/sessions")
def list_chat_sessions():
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    rows = AIChatSession.query.filter_by(user_id=user.id).order_by(AIChatSession.updated_at.desc()).limit(50).all()
    return jsonify(sessions=[
        {"id": row.id, "title": row.title, "created_at": _iso_utc(row.created_at), "updated_at": _iso_utc(row.updated_at)}
        for row in rows
    ])


@ai_bp.get("/chat/sessions/<int:session_id>")
def get_chat_session(session_id):
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    row = AIChatSession.query.filter_by(id=session_id, user_id=user.id).first()
    if not row:
        return jsonify(error="Conversation not found."), 404
    messages = AIChatMessage.query.filter_by(session_id=row.id, user_id=user.id).order_by(AIChatMessage.created_at, AIChatMessage.id).all()
    return jsonify(
        session={"id": row.id, "title": row.title, "created_at": _iso_utc(row.created_at)},
        messages=[{"id": message.id, "role": message.role, "content": message.content, "source": message.source, "created_at": _iso_utc(message.created_at)} for message in messages],
    )


@ai_bp.post("/chat")
def chat():
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    data = _request_data()
    if data is None:
        return jsonify(error="Request body must be a JSON object."), 400
    message_text = data.get("message")
    if not isinstance(message_text, str) or not message_text.strip() or len(message_text.strip()) > 2000:
        return jsonify(error="Message must contain 1 to 2,000 characters."), 400
    message_text = message_text.strip()
    session_id = data.get("session_id")
    if session_id is not None and (isinstance(session_id, bool) or not isinstance(session_id, int)):
        return jsonify(error="Conversation ID must be an integer."), 400
    conversation = AIChatSession.query.filter_by(id=session_id, user_id=user.id).first() if session_id is not None else None
    if session_id is not None and not conversation:
        return jsonify(error="Conversation not found."), 404
    if conversation is None:
        conversation = AIChatSession(user_id=user.id, title=message_text[:96])
        db.session.add(conversation)
        db.session.flush()

    previous_messages = AIChatMessage.query.filter_by(session_id=conversation.id, user_id=user.id).order_by(AIChatMessage.id.desc()).limit(8).all()
    previous_messages.reverse()
    stored_user_message = AIChatMessage(session_id=conversation.id, user_id=user.id, role="user", content=message_text, source="user")
    db.session.add(stored_user_message)
    conversation.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    profile = {"goal": "placement preparation"}
    performance_history = _recent_performance(user)
    context = {"student_profile": profile, "recent_assessment_history": _external_performance(performance_history)}
    messages = [{
        "role": "system",
        "content": "You are Prepwise, a concise and encouraging placement-preparation tutor. Help with aptitude, logical reasoning, verbal ability, programming, data structures and algorithms, and interview preparation. Personalize advice using the supplied profile and real assessment history only; never invent a score or student detail. For other topics, politely guide the student back to placement preparation. Student context:\n" + json.dumps(context, ensure_ascii=False),
    }]
    messages.extend({"role": item.role, "content": _redact_contact_details(item.content)} for item in previous_messages if item.role in ("user", "assistant"))
    messages.append({"role": "user", "content": _redact_contact_details(message_text)})

    source = "nemotron"
    try:
        reply = NemotronClient().complete(messages, max_tokens=800).strip()
        if not 1 <= len(reply) <= 6000:
            raise NemotronUnavailable("Nemotron returned an invalid message length.")
    except (NemotronUnavailable, ValueError, TypeError):
        source = "fallback"
        reply = fallback_chat_reply(message_text, {"name": user.name, **profile}, performance_history)

    assistant_message = AIChatMessage(session_id=conversation.id, user_id=user.id, role="assistant", content=reply, source=source)
    conversation.updated_at = datetime.now(timezone.utc)
    db.session.add(assistant_message)
    db.session.commit()
    return jsonify(
        session_id=conversation.id,
        source=source,
        user_message={"id": stored_user_message.id, "role": "user", "content": stored_user_message.content, "created_at": _iso_utc(stored_user_message.created_at)},
        assistant_message={"id": assistant_message.id, "role": "assistant", "content": assistant_message.content, "source": source, "created_at": _iso_utc(assistant_message.created_at)},
    ), 201


@ai_bp.get("/practice-questions")
def list_practice_questions():
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    rows = AIPracticeQuestion.query.filter_by(user_id=user.id).order_by(AIPracticeQuestion.created_at.desc()).limit(30).all()
    return jsonify(questions=[
        {"id": row.id, "subject": row.subject, "prompt": row.prompt, "options": row.options, "correct_option": row.correct_option, "explanation": row.explanation, "source": row.source, "created_at": _iso_utc(row.created_at)}
        for row in rows
    ])


@ai_bp.post("/practice-questions")
def generate_practice_question():
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    data = _request_data()
    if data is None:
        return jsonify(error="Request body must be a JSON object."), 400
    subject = data.get("subject")
    if subject not in SUBJECTS:
        return jsonify(error=f"Choose one of: {', '.join(SUBJECTS)}."), 400
    attempt = None
    attempt_id = data.get("attempt_id")
    if attempt_id is not None:
        if isinstance(attempt_id, bool) or not isinstance(attempt_id, int):
            return jsonify(error="Assessment ID must be an integer."), 400
        attempt = AssessmentAttempt.query.filter_by(id=attempt_id, user_id=user.id).filter(AssessmentAttempt.completed_at.isnot(None)).first()
        if not attempt:
            return jsonify(error="Completed assessment not found."), 404
    else:
        attempt = AssessmentAttempt.query.filter_by(user_id=user.id).filter(AssessmentAttempt.completed_at.isnot(None)).order_by(AssessmentAttempt.completed_at.desc()).first()
    score_context = next((row for row in _scores_for_attempt(attempt) if row["subject"] == subject), None) if attempt else None
    context = {
        "goal": "placement preparation",
        "subject": subject,
        "latest_subject_performance": {"subject": subject, "performance": score_context["insight"]} if score_context else None,
    }
    prompt = [
        {"role": "system", "content": "Create one original, accurate placement-preparation MCQ. Return exactly one JSON object with keys subject, prompt, options, correct_option, explanation. Options must contain exactly four distinct strings. correct_option is a zero-based integer from 0 to 3. Include a concise, accurate explanation. Do not include markdown or text outside JSON."},
        {"role": "user", "content": "Generate a question using this context. Do not make any claim about the student beyond the supplied result:\n" + json.dumps(context, ensure_ascii=False)},
    ]
    source = "nemotron"
    try:
        question_data = validate_practice_question(NemotronClient().complete_json(prompt, max_tokens=800), subject)
    except (NemotronUnavailable, ValueError, TypeError):
        source = "question_bank"
        bank_question = Question.query.filter_by(subject=subject).order_by(Question.id).first()
        if not bank_question:
            return jsonify(error="No fallback questions are available for this subject."), 503
        question_data = validate_practice_question({
            "subject": bank_question.subject,
            "prompt": bank_question.prompt,
            "options": bank_question.options,
            "correct_option": bank_question.correct_option,
            "explanation": bank_question.explanation,
        }, subject)

    row = AIPracticeQuestion(user_id=user.id, **question_data, source=source)
    db.session.add(row)
    db.session.commit()
    return jsonify(question={
        "id": row.id,
        "subject": row.subject,
        "prompt": row.prompt,
        "options": row.options,
        "correct_option": row.correct_option,
        "explanation": row.explanation,
        "source": row.source,
        "created_at": _iso_utc(row.created_at),
    }), 201

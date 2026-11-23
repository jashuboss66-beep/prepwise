from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from ..extensions import db
from ..models import (
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentAttemptQuestion,
    AssessmentSubjectResult,
    Question,
    RewardTransaction,
    User,
)
from ..services.gamification import _reward_payload, award_activity

assessments_bp = Blueprint("assessments", __name__, url_prefix="/api/assessments")
ASSESSMENT_DURATION_SECONDS = 20 * 60


def _current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def _owned_attempt(attempt_id, user):
    return AssessmentAttempt.query.filter_by(id=attempt_id, user_id=user.id).first()


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _iso_utc(value):
    return _utc(value).isoformat().replace("+00:00", "Z")


def _insight(score):
    if score >= 70:
        return "Strength"
    if score < 50:
        return "Needs focus"
    return "Developing"


def _option_order(member):
    order = member.option_order or [0, 1, 2, 3]
    return order if sorted(order) == [0, 1, 2, 3] else [0, 1, 2, 3]


def _display_index(order, canonical_index):
    return order.index(canonical_index) if canonical_index in order else None


def _result_payload(attempt):
    subject_results = AssessmentSubjectResult.query.filter_by(attempt_id=attempt.id).order_by(AssessmentSubjectResult.subject).all()
    review = (
        db.session.query(AssessmentAttemptQuestion, Question, AssessmentAnswer)
        .join(Question, Question.id == AssessmentAttemptQuestion.question_id)
        .outerjoin(
            AssessmentAnswer,
            (AssessmentAnswer.attempt_id == AssessmentAttemptQuestion.attempt_id)
            & (AssessmentAnswer.question_id == AssessmentAttemptQuestion.question_id),
        )
        .filter(AssessmentAttemptQuestion.attempt_id == attempt.id)
        .order_by(AssessmentAttemptQuestion.position)
        .all()
    )
    reward = RewardTransaction.query.filter_by(user_id=attempt.user_id, activity_type="assessment", activity_id=attempt.id).first()
    return {
        "reward": _reward_payload(reward) if reward else None,
        "attempt": {
            "id": attempt.id,
            "started_at": _iso_utc(attempt.started_at),
            "completed_at": _iso_utc(attempt.completed_at),
            "duration_seconds": attempt.duration_seconds,
            "correct_answers": attempt.correct_answers,
            "total_questions": attempt.total_questions,
            "score_percent": attempt.score_percent,
            "assessment_mode": attempt.assessment_mode or "initial",
            "assessment_category": attempt.assessment_category,
            "difficulty": attempt.difficulty,
        },
        "subjects": [
            {
                "subject": row.subject,
                "correct_answers": row.correct_answers,
                "total_questions": row.total_questions,
                "score_percent": row.score_percent,
                "insight": row.insight,
            }
            for row in subject_results
        ],
        "questions": [
            {
                "id": question.id,
                "subject": question.subject,
                "category": question.category,
                "topic": question.topic,
                "difficulty": question.difficulty,
                "prompt": question.prompt,
                "options": [question.options[index] for index in _option_order(member)],
                "selected_option": _display_index(_option_order(member), answer.selected_option) if answer and answer.selected_option is not None else None,
                "correct_option": _display_index(_option_order(member), question.correct_option),
                "is_correct": bool(answer and answer.is_correct),
                "time_spent_seconds": answer.time_spent_seconds if answer else None,
                "explanation": question.explanation,
            }
            for member, question, answer in review
        ],
    }


def _complete_attempt(attempt):
    questions = (
        db.session.query(Question)
        .join(AssessmentAttemptQuestion, AssessmentAttemptQuestion.question_id == Question.id)
        .filter(AssessmentAttemptQuestion.attempt_id == attempt.id)
        .order_by(AssessmentAttemptQuestion.position)
        .all()
    )
    subject_totals = {}
    correct_total = 0
    for question in questions:
        answer = AssessmentAnswer.query.filter_by(attempt_id=attempt.id, question_id=question.id).first()
        if answer is None:
            answer = AssessmentAnswer(attempt_id=attempt.id, question_id=question.id, selected_option=None)
            db.session.add(answer)
        answer.is_correct = answer.selected_option == question.correct_option
        answer.answered_at = datetime.now(timezone.utc)
        correct_total += int(answer.is_correct)
        totals = subject_totals.setdefault(question.subject, {"correct": 0, "total": 0})
        totals["total"] += 1
        totals["correct"] += int(answer.is_correct)

    attempt.correct_answers = correct_total
    attempt.total_questions = len(questions)
    attempt.score_percent = round(correct_total * 100 / len(questions), 1) if questions else 0.0
    attempt.completed_at = datetime.now(timezone.utc)
    for subject, totals in subject_totals.items():
        percentage = round(totals["correct"] * 100 / totals["total"], 1)
        db.session.add(AssessmentSubjectResult(
            attempt_id=attempt.id,
            subject=subject,
            correct_answers=totals["correct"],
            total_questions=totals["total"],
            score_percent=percentage,
            insight=_insight(percentage),
        ))
    answered_count = AssessmentAnswer.query.filter_by(attempt_id=attempt.id).filter(AssessmentAnswer.selected_option.isnot(None)).count()
    award_activity(attempt.user_id, "assessment", attempt.id, correct_total, len(questions), answered=answered_count)
    from ..services.learning import missions_payload
    missions_payload(attempt.user_id)
    db.session.commit()
    return _result_payload(attempt)


@assessments_bp.post("")
def start_assessment():
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    questions = Question.query.filter_by(practice_only=False).order_by(Question.subject, Question.id).all()
    if not questions:
        return jsonify(error="The question bank is empty."), 503
    attempt = AssessmentAttempt(
        user_id=user.id,
        duration_seconds=ASSESSMENT_DURATION_SECONDS,
        total_questions=len(questions),
    )
    db.session.add(attempt)
    db.session.flush()
    db.session.add_all(
        AssessmentAttemptQuestion(attempt_id=attempt.id, question_id=question.id, position=position)
        for position, question in enumerate(questions)
    )
    db.session.commit()
    return jsonify(attempt_id=attempt.id), 201


@assessments_bp.get("/history")
def assessment_history():
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    attempts = AssessmentAttempt.query.filter_by(user_id=user.id).order_by(AssessmentAttempt.started_at.desc()).all()
    return jsonify(attempts=[
        {
            "id": attempt.id,
            "started_at": _iso_utc(attempt.started_at),
            "completed_at": _iso_utc(attempt.completed_at) if attempt.completed_at else None,
            "status": "completed" if attempt.completed_at else "in_progress",
            "correct_answers": attempt.correct_answers,
            "total_questions": attempt.total_questions,
            "score_percent": attempt.score_percent,
            "assessment_mode": attempt.assessment_mode or "initial",
            "assessment_category": attempt.assessment_category,
            "difficulty": attempt.difficulty,
        }
        for attempt in attempts
    ])


@assessments_bp.get("/<int:attempt_id>")
def get_assessment(attempt_id):
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    attempt = _owned_attempt(attempt_id, user)
    if not attempt:
        return jsonify(error="Assessment not found."), 404
    if attempt.completed_at:
        return jsonify(status="completed", result_url=f"/assessment/{attempt.id}/results")
    rows = (
        db.session.query(AssessmentAttemptQuestion, Question, AssessmentAnswer)
        .join(Question, Question.id == AssessmentAttemptQuestion.question_id)
        .outerjoin(
            AssessmentAnswer,
            (AssessmentAnswer.attempt_id == AssessmentAttemptQuestion.attempt_id)
            & (AssessmentAnswer.question_id == AssessmentAttemptQuestion.question_id),
        )
        .filter(AssessmentAttemptQuestion.attempt_id == attempt.id)
        .order_by(AssessmentAttemptQuestion.position)
        .all()
    )
    return jsonify(
        status="in_progress",
        attempt={"id": attempt.id, "started_at": _iso_utc(attempt.started_at), "duration_seconds": attempt.duration_seconds,
                 "assessment_mode": attempt.assessment_mode or "initial", "assessment_category": attempt.assessment_category,
                 "difficulty": attempt.difficulty},
        questions=[
            {
                "id": question.id,
                "subject": question.subject,
                "category": question.category,
                "topic": question.topic,
                "difficulty": question.difficulty,
                "prompt": question.prompt,
                "options": [question.options[index] for index in _option_order(member)],
                "selected_option": _display_index(_option_order(member), answer.selected_option) if answer and answer.selected_option is not None else None,
            }
            for member, question, answer in rows
        ],
    )


@assessments_bp.put("/<int:attempt_id>/answers")
def save_answer(attempt_id):
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    attempt = _owned_attempt(attempt_id, user)
    if not attempt:
        return jsonify(error="Assessment not found."), 404
    if attempt.completed_at:
        return jsonify(error="This assessment has already been submitted."), 409
    if (datetime.now(timezone.utc) - _utc(attempt.started_at)).total_seconds() >= attempt.duration_seconds:
        return jsonify(error="Time is up. Submit your assessment to see your results."), 409

    data = request.get_json(silent=True) or {}
    question_id = data.get("question_id")
    selected_option = data.get("selected_option")
    if not isinstance(question_id, int) or isinstance(question_id, bool):
        return jsonify(error="A valid question is required."), 400
    if selected_option is not None and (not isinstance(selected_option, int) or isinstance(selected_option, bool) or selected_option not in range(4)):
        return jsonify(error="Choose one of the available answers."), 400
    member = AssessmentAttemptQuestion.query.filter_by(attempt_id=attempt.id, question_id=question_id).first()
    if not member:
        return jsonify(error="That question is not part of this assessment."), 404
    answer = AssessmentAnswer.query.filter_by(attempt_id=attempt.id, question_id=question_id).first()
    if answer is None:
        answer = AssessmentAnswer(attempt_id=attempt.id, question_id=question_id)
        db.session.add(answer)
    order = _option_order(member)
    canonical_option = order[selected_option] if selected_option is not None else None
    now = datetime.now(timezone.utc)
    answer.selected_option = canonical_option
    answer.answered_at = now
    if member.first_viewed_at:
        view_time = _utc(member.first_viewed_at)
        answer.time_spent_seconds = min(attempt.duration_seconds, max(0, int((now - view_time).total_seconds())))
    db.session.commit()
    return jsonify(saved=True)


@assessments_bp.post("/<int:attempt_id>/questions/<int:question_id>/view")
def mark_question_viewed(attempt_id, question_id):
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    attempt = _owned_attempt(attempt_id, user)
    if not attempt:
        return jsonify(error="Assessment not found."), 404
    if attempt.completed_at:
        return jsonify(error="This assessment has already been submitted."), 409
    member = AssessmentAttemptQuestion.query.filter_by(attempt_id=attempt.id, question_id=question_id).first()
    if not member:
        return jsonify(error="That question is not part of this assessment."), 404
    if member.first_viewed_at is None:
        member.first_viewed_at = datetime.now(timezone.utc)
        db.session.commit()
    return jsonify(viewed=True)


@assessments_bp.post("/<int:attempt_id>/submit")
def submit_assessment(attempt_id):
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    attempt = _owned_attempt(attempt_id, user)
    if not attempt:
        return jsonify(error="Assessment not found."), 404
    if attempt.completed_at:
        return jsonify(_result_payload(attempt))
    return jsonify(_complete_attempt(attempt))


@assessments_bp.get("/<int:attempt_id>/results")
def assessment_results(attempt_id):
    user = _current_user()
    if not user:
        return jsonify(error="Authentication required."), 401
    attempt = _owned_attempt(attempt_id, user)
    if not attempt:
        return jsonify(error="Assessment not found."), 404
    if not attempt.completed_at:
        return jsonify(error="Submit the assessment to view results."), 409
    return jsonify(_result_payload(attempt))

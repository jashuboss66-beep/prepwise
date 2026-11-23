from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, session
from ..extensions import db
from ..models import PracticeAttempt, PracticeSession, PracticeSessionQuestion, Question, User
from ..services.adaptive import TOPICS, mastery_snapshot, pick_questions
from ..services.gamification import award_activity

practice_bp = Blueprint("practice", __name__, url_prefix="/api/practice")

def _user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None

def _question_payload(question, position):
    return {"id": question.id, "subject": question.subject, "topic": question.topic, "difficulty": question.difficulty,
            "prompt": question.prompt, "options": question.options, "position": position}

@practice_bp.get("/progress")
def progress():
    user = _user()
    if not user: return jsonify(error="Authentication required."), 401
    return jsonify(mastery_snapshot(user.id))

@practice_bp.get("/topics")
def topics():
    user = _user()
    if not user: return jsonify(error="Authentication required."), 401
    return jsonify(subjects=[{"subject": subject, "topics": names} for subject, names in TOPICS.items()])

@practice_bp.post("/sessions")
def start_session():
    user = _user()
    if not user: return jsonify(error="Authentication required."), 401
    data = request.get_json(silent=True) or {}
    subject, topic = data.get("subject"), data.get("topic") or None
    if subject not in TOPICS or (topic and topic not in TOPICS[subject]):
        return jsonify(error="Choose a valid subject and topic."), 400
    questions, target = pick_questions(user.id, subject, topic, limit=5)
    if not questions: return jsonify(error="No questions are available for that topic yet."), 404
    practice_session = PracticeSession(user_id=user.id, subject=subject, topic=topic)
    db.session.add(practice_session); db.session.flush()
    db.session.add_all(PracticeSessionQuestion(session_id=practice_session.id, question_id=q.id, position=i) for i, q in enumerate(questions))
    db.session.commit()
    return jsonify(session={"id": practice_session.id, "subject": subject, "topic": topic, "target_difficulty": target,
                           "questions": [_question_payload(q, i) for i, q in enumerate(questions)]}), 201

@practice_bp.post("/sessions/<int:session_id>/submit")
def submit_session(session_id):
    user = _user()
    if not user: return jsonify(error="Authentication required."), 401
    practice_session = PracticeSession.query.filter_by(id=session_id, user_id=user.id).first()
    if not practice_session: return jsonify(error="Practice session not found."), 404
    if practice_session.completed_at: return jsonify(error="This practice session was already submitted."), 409
    answers = (request.get_json(silent=True) or {}).get("answers")
    if not isinstance(answers, list): return jsonify(error="Answers must be a list."), 400
    submitted = {}
    for answer in answers:
        if not isinstance(answer, dict) or not isinstance(answer.get("question_id"), int):
            return jsonify(error="Each answer needs a valid question ID."), 400
        selected = answer.get("selected_option")
        if selected is not None and (not isinstance(selected, int) or isinstance(selected, bool) or selected not in range(4)):
            return jsonify(error="Choose one of the available options."), 400
        submitted[answer["question_id"]] = selected
    rows = (db.session.query(PracticeSessionQuestion, Question).join(Question, Question.id == PracticeSessionQuestion.question_id)
            .filter(PracticeSessionQuestion.session_id == practice_session.id).order_by(PracticeSessionQuestion.position).all())
    if set(submitted) - {member.question_id for member, _ in rows}:
        return jsonify(error="An answer refers to a question outside this session."), 400
    now, results, correct_count = datetime.now(timezone.utc), [], 0
    for member, question in rows:
        selected = submitted.get(question.id); correct = selected == question.correct_option
        member.selected_option, member.is_correct, member.answered_at = selected, correct, now
        correct_count += int(correct)
        db.session.add(PracticeAttempt(user_id=user.id, session_id=practice_session.id, question_id=question.id,
            subject=question.subject, topic=question.topic, difficulty=question.difficulty,
            selected_option=selected, is_correct=correct, attempted_at=now))
        results.append({**_question_payload(question, member.position), "selected_option": selected,
                        "correct_option": question.correct_option, "is_correct": correct, "explanation": question.explanation})
    practice_session.completed_at = now
    answered_count = sum(selected is not None for selected in submitted.values())
    reward = award_activity(user.id, "practice", practice_session.id, correct_count, len(rows), topic=practice_session.topic, answered=answered_count)
    from ..services.learning import missions_payload
    missions_payload(user.id)
    db.session.commit()
    total = len(rows)
    return jsonify(result={"session_id": practice_session.id, "correct": correct_count, "total": total,
                           "accuracy": round(correct_count * 100 / total, 1) if total else 0, "questions": results},
                   progress=mastery_snapshot(user.id), reward=reward)

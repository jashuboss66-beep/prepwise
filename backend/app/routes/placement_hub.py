import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request, session

from ..extensions import db
from ..models import (
    AssessmentAttempt, AssessmentAttemptQuestion, PracticeAttempt, PracticeSession,
    PracticeSessionQuestion, Question, QuestionBookmark, RewardTransaction, User,
)
from ..services.adaptive import TOPICS
from ..services.gamification import _reward_payload, award_activity

hub_bp = Blueprint("placement_hub", __name__, url_prefix="/api/hub")
CATEGORY_SUBJECTS = {"Aptitude": ["Aptitude"], "Communication": ["Verbal Ability"],
                     "Technical": ["Technical"], "Full placement": ["Aptitude", "Verbal Ability", "Technical"]}


def _user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def _utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _cutoff():
    return current_app.config.get("DAILY_QUIZ_CUTOFF_UTC_HOUR", 23)


def _deadline(quiz_day):
    return datetime.combine(quiz_day, time(_cutoff()), tzinfo=timezone.utc)


def _question_payload(question, position, bookmarked=False, selected_option=None, reveal=False):
    result = {"id": question.id, "position": position, "category": question.category, "subject": question.subject,
              "topic": question.topic, "difficulty": question.difficulty, "prompt": question.prompt,
              "options": question.options, "bookmarked": bookmarked, "selected_option": selected_option,
              "source": question.source, "license": question.license}
    if reveal:
        result.update(correct_option=question.correct_option, explanation=question.explanation)
    return result


def _recent_question_ids(user_id):
    practice_ids = {row[0] for row in db.session.query(PracticeAttempt.question_id).filter_by(user_id=user_id).order_by(
        PracticeAttempt.attempted_at.desc()).limit(400).all()}
    assessment_ids = {row[0] for row in db.session.query(AssessmentAttemptQuestion.question_id)
        .join(AssessmentAttempt, AssessmentAttempt.id == AssessmentAttemptQuestion.attempt_id)
        .filter(AssessmentAttempt.user_id == user_id).order_by(AssessmentAttempt.started_at.desc()).limit(400).all()}
    return practice_ids | assessment_ids


def _eligible_questions(user_id, category, topic=None, difficulty=None, bookmarked_only=False, incorrect_only=False):
    query = Question.query.filter(Question.category == category)
    if topic:
        query = query.filter_by(topic=topic)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if bookmarked_only:
        query = query.join(QuestionBookmark, QuestionBookmark.question_id == Question.id).filter(QuestionBookmark.user_id == user_id)
    if incorrect_only:
        incorrect_ids = db.session.query(PracticeAttempt.question_id).filter_by(user_id=user_id, is_correct=False).distinct()
        query = query.filter(Question.id.in_(incorrect_ids))
    return query.order_by(Question.id).all()


@hub_bp.get("/taxonomy")
def taxonomy():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    rows = (db.session.query(Question.category, Question.topic).filter(Question.category.in_(CATEGORY_SUBJECTS))
            .distinct().order_by(Question.category, Question.topic).all())
    categories = defaultdict(list)
    for category, topic in rows:
        categories[category].append(topic)
    return jsonify(categories=[{"name": name, "topics": categories[name]} for name in CATEGORY_SUBJECTS if name != "Full placement"])


@hub_bp.get("/overview")
def overview():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    normal_rows = (PracticeAttempt.query.join(PracticeSession, PracticeSession.id == PracticeAttempt.session_id)
        .filter(PracticeAttempt.user_id == user.id, PracticeSession.mode == "normal", PracticeAttempt.selected_option.isnot(None)).all())
    ai_attempts = AssessmentAttempt.query.filter_by(user_id=user.id, assessment_mode="ai").filter(
        AssessmentAttempt.completed_at.isnot(None)).order_by(AssessmentAttempt.completed_at.desc()).all()
    latest_change = None
    if ai_attempts:
        previous = next((row for row in ai_attempts[1:] if row.assessment_category == ai_attempts[0].assessment_category), None)
        if previous:
            latest_change = round(ai_attempts[0].score_percent - previous.score_percent, 1)
    today = datetime.now(timezone.utc).date()
    daily = PracticeSession.query.filter_by(user_id=user.id, mode="daily_quiz", quiz_date=today).first()
    daily_score = None
    if daily and daily.completed_at:
        data = _daily_result(user.id, daily)
        daily_score = {"score": data["score"], "total": data["total"], "accuracy": data["accuracy"], "completed": True}
    return jsonify(practice={"attempted": len(normal_rows), "correct": sum(bool(row.is_correct) for row in normal_rows),
        "accuracy": round(sum(bool(row.is_correct) for row in normal_rows) * 100 / len(normal_rows), 1) if normal_rows else None},
        ai_assessments=[{"id": row.id, "category": row.assessment_category, "score": row.score_percent,
                         "completed_at": row.completed_at.isoformat()} for row in ai_attempts[:5]],
        recent_improvement=latest_change, daily_quiz=daily_score)


@hub_bp.post("/normal/sessions")
def start_normal_session():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    data = request.get_json(silent=True) or {}
    category, topic, difficulty = data.get("category"), data.get("topic"), data.get("difficulty")
    count = data.get("count", 5)
    if category not in ("Aptitude", "Communication", "Technical"):
        return jsonify(error="Choose Aptitude, Communication, or Technical."), 400
    if topic and topic not in {row[0] for row in db.session.query(Question.topic).filter_by(category=category).distinct().all()}:
        return jsonify(error="Choose a valid topic for this category."), 400
    if difficulty not in (None, "", "any", "easy", "medium", "hard"):
        return jsonify(error="Difficulty must be Easy, Medium, or Hard."), 400
    if not isinstance(count, int) or isinstance(count, bool) or count < 1 or count > 20:
        return jsonify(error="Choose between 1 and 20 questions."), 400
    bookmarked_only = data.get("bookmarked_only", False)
    incorrect_only = data.get("incorrect_only", False)
    if not isinstance(bookmarked_only, bool) or not isinstance(incorrect_only, bool):
        return jsonify(error="Practice filters must be true or false."), 400
    pool = _eligible_questions(user.id, category, topic, difficulty if difficulty not in (None, "", "any") else None,
                               bookmarked_only, incorrect_only)
    if not pool:
        return jsonify(error="No matching questions are available. Try a different topic or filter."), 404
    if not incorrect_only and not bookmarked_only:
        recent = _recent_question_ids(user.id)
        unseen = [row for row in pool if row.id not in recent]
        pool = unseen if len(unseen) >= count else unseen + [row for row in pool if row not in unseen]
    random.SystemRandom().shuffle(pool)
    selected = pool[:min(count, len(pool))]
    subject = CATEGORY_SUBJECTS[category][0]
    chosen_topic = topic or (selected[0].topic if selected else None)
    practice_session = PracticeSession(user_id=user.id, subject=subject, topic=chosen_topic, mode="normal")
    db.session.add(practice_session)
    db.session.flush()
    db.session.add_all(PracticeSessionQuestion(session_id=practice_session.id, question_id=row.id, position=i)
                       for i, row in enumerate(selected))
    db.session.commit()
    bookmarks = {row.question_id for row in QuestionBookmark.query.filter_by(user_id=user.id).filter(
        QuestionBookmark.question_id.in_([q.id for q in selected])).all()}
    return jsonify(session={"id": practice_session.id, "category": category, "topic": chosen_topic,
        "questions": [_question_payload(row, i, row.id in bookmarks) for i, row in enumerate(selected)]}), 201


@hub_bp.post("/normal/sessions/<int:session_id>/answer")
def answer_normal_question(session_id):
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    practice_session = PracticeSession.query.filter_by(id=session_id, user_id=user.id, mode="normal").first()
    if not practice_session:
        return jsonify(error="Practice session not found."), 404
    if practice_session.completed_at:
        return jsonify(error="This practice session is complete."), 409
    data = request.get_json(silent=True) or {}
    question_id, selected = data.get("question_id"), data.get("selected_option")
    if not isinstance(question_id, int) or isinstance(question_id, bool):
        return jsonify(error="A valid question is required."), 400
    if not isinstance(selected, int) or isinstance(selected, bool) or selected not in range(4):
        return jsonify(error="Choose one of the four answers."), 400
    member = PracticeSessionQuestion.query.filter_by(session_id=session_id, question_id=question_id).first()
    if not member:
        return jsonify(error="That question is not part of this session."), 404
    question = db.session.get(Question, question_id)
    correct = selected == question.correct_option
    now = datetime.now(timezone.utc)
    member.selected_option, member.is_correct, member.answered_at = selected, correct, now
    attempt = PracticeAttempt.query.filter_by(user_id=user.id, session_id=session_id, question_id=question_id).first()
    if attempt is None:
        attempt = PracticeAttempt(user_id=user.id, session_id=session_id, question_id=question_id,
            subject=question.subject, topic=question.topic, difficulty=question.difficulty,
            selected_option=selected, is_correct=correct, attempted_at=now)
        db.session.add(attempt)
    else:
        attempt.selected_option, attempt.is_correct, attempt.attempted_at = selected, correct, now
    db.session.commit()
    bookmark = QuestionBookmark.query.filter_by(user_id=user.id, question_id=question_id).first() is not None
    return jsonify(answer={"question_id": question_id, "selected_option": selected, "is_correct": correct,
        "correct_option": question.correct_option, "explanation": question.explanation,
        "topic": question.topic, "category": question.category, "bookmarked": bookmark})


@hub_bp.post("/normal/sessions/<int:session_id>/complete")
def complete_normal_session(session_id):
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    practice_session = PracticeSession.query.filter_by(id=session_id, user_id=user.id, mode="normal").first()
    if not practice_session:
        return jsonify(error="Practice session not found."), 404
    existing = RewardTransaction.query.filter_by(user_id=user.id, activity_type="practice", activity_id=session_id).first()
    if practice_session.completed_at:
        return jsonify(completed=True, reward=_reward_payload(existing) if existing else None)
    rows = PracticeAttempt.query.filter_by(user_id=user.id, session_id=session_id).all()
    if not rows:
        return jsonify(error="Answer at least one question before completing this practice set."), 409
    now = datetime.now(timezone.utc)
    practice_session.completed_at = now
    correct = sum(int(row.is_correct) for row in rows)
    reward = award_activity(user.id, "practice", session_id, correct, len(rows), topic=practice_session.topic,
                            answered=sum(row.selected_option is not None for row in rows), now=now)
    from ..services.learning import missions_payload
    missions_payload(user.id)
    db.session.commit()
    return jsonify(completed=True, reward=reward)


@hub_bp.put("/bookmarks/<int:question_id>")
def set_bookmark(question_id):
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    if not db.session.get(Question, question_id):
        return jsonify(error="Question not found."), 404
    data = request.get_json(silent=True) or {}
    bookmarked = data.get("bookmarked")
    if not isinstance(bookmarked, bool):
        return jsonify(error="bookmarked must be true or false."), 400
    row = QuestionBookmark.query.filter_by(user_id=user.id, question_id=question_id).first()
    if bookmarked and row is None:
        db.session.add(QuestionBookmark(user_id=user.id, question_id=question_id))
    elif not bookmarked and row:
        db.session.delete(row)
    db.session.commit()
    return jsonify(question_id=question_id, bookmarked=bookmarked)


@hub_bp.get("/bookmarks")
def bookmarks():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    rows = (db.session.query(QuestionBookmark, Question).join(Question, Question.id == QuestionBookmark.question_id)
            .filter(QuestionBookmark.user_id == user.id).order_by(QuestionBookmark.created_at.desc()).limit(250).all())
    return jsonify(questions=[{**_question_payload(question, index, True), "bookmarked_at": bookmark.created_at.isoformat()}
                              for index, (bookmark, question) in enumerate(rows)])


@hub_bp.get("/normal/history")
def normal_history():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    attempts = (PracticeAttempt.query.join(PracticeSession, PracticeSession.id == PracticeAttempt.session_id)
                .filter(PracticeAttempt.user_id == user.id, PracticeSession.mode == "normal")
                .order_by(PracticeAttempt.attempted_at.desc()).limit(100).all())
    return jsonify(attempts=[{"question_id": row.question_id, "category": db.session.get(Question, row.question_id).category,
        "subject": row.subject, "topic": row.topic, "difficulty": row.difficulty, "is_correct": row.is_correct,
        "attempted_at": row.attempted_at.isoformat()} for row in attempts])


@hub_bp.post("/assessments")
def start_ai_assessment():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    data = request.get_json(silent=True) or {}
    category, difficulty = data.get("category"), data.get("difficulty")
    count, duration = data.get("question_count"), data.get("duration_minutes")
    if category not in CATEGORY_SUBJECTS:
        return jsonify(error="Choose an assessment category."), 400
    if difficulty not in ("easy", "medium", "hard", "mixed"):
        return jsonify(error="Choose Easy, Medium, Hard, or Mixed difficulty."), 400
    if not isinstance(count, int) or isinstance(count, bool) or count < 5 or count > 50:
        return jsonify(error="Question count must be between 5 and 50."), 400
    if not isinstance(duration, int) or isinstance(duration, bool) or duration < 1 or duration > 180:
        return jsonify(error="Duration must be between 1 and 180 minutes."), 400
    query = Question.query.filter(Question.category.in_(CATEGORY_SUBJECTS[category]))
    if difficulty != "mixed":
        query = query.filter_by(difficulty=difficulty)
    pool = query.all()
    if len(pool) < count:
        return jsonify(error=f"Only {len(pool)} questions match these settings. Choose fewer questions or mixed difficulty."), 400
    recent = _recent_question_ids(user.id)
    unseen = [row for row in pool if row.id not in recent]
    candidates = unseen if len(unseen) >= count else unseen + [row for row in pool if row not in unseen]
    random.SystemRandom().shuffle(candidates)
    selected = candidates[:count]
    attempt = AssessmentAttempt(user_id=user.id, duration_seconds=duration * 60, total_questions=count,
        assessment_mode="ai", assessment_category=category, difficulty=difficulty)
    db.session.add(attempt)
    db.session.flush()
    secure_random = random.SystemRandom()
    db.session.add_all(AssessmentAttemptQuestion(attempt_id=attempt.id, question_id=question.id,
        position=position, option_order=secure_random.sample([0, 1, 2, 3], 4)) for position, question in enumerate(selected))
    db.session.commit()
    return jsonify(attempt_id=attempt.id, category=category, question_count=count,
                   duration_seconds=duration * 60), 201


def _daily_quiz_session(user_id, now=None):
    now = _utc(now or datetime.now(timezone.utc))
    today_session = PracticeSession.query.filter_by(user_id=user_id, mode="daily_quiz", quiz_date=now.date()).first()
    if today_session:
        return today_session
    quiz_day = now.date() + timedelta(days=1) if now >= _deadline(now.date()) else now.date()
    existing = PracticeSession.query.filter_by(user_id=user_id, mode="daily_quiz", quiz_date=quiz_day).first()
    if existing:
        return existing
    specs = [("Aptitude", 4), ("Communication", 3), ("Technical", 3)]
    recent = _recent_question_ids(user_id)
    selected = []
    for category, count in specs:
        pool = Question.query.filter_by(category=category).all()
        fresh = [row for row in pool if row.id not in recent and row not in selected]
        if len(fresh) < count:
            fresh += [row for row in pool if row not in fresh and row not in selected]
        random.SystemRandom().shuffle(fresh)
        selected.extend(fresh[:count])
    if len(selected) < 10:
        raise ValueError("The question bank does not contain enough questions for a daily quiz.")
    daily = PracticeSession(user_id=user_id, subject="Daily Quiz", topic=quiz_day.isoformat(), mode="daily_quiz", quiz_date=quiz_day)
    db.session.add(daily)
    db.session.flush()
    db.session.add_all(PracticeSessionQuestion(session_id=daily.id, question_id=row.id, position=index)
                       for index, row in enumerate(selected))
    db.session.flush()
    return daily


def _daily_result(user_id, daily):
    rows = (db.session.query(PracticeSessionQuestion, Question).join(Question, Question.id == PracticeSessionQuestion.question_id)
            .filter(PracticeSessionQuestion.session_id == daily.id).order_by(PracticeSessionQuestion.position).all())
    result_questions = []
    for member, question in rows:
        result_questions.append({**_question_payload(question, member.position, selected_option=member.selected_option,
            reveal=daily.completed_at is not None), "is_correct": bool(member.is_correct)})
    answered_members = [member for member, _ in rows if member.selected_option is not None]
    correct = sum(int(member.is_correct is True) for member in answered_members)
    reward = RewardTransaction.query.filter_by(user_id=user_id, activity_type="practice", activity_id=daily.id).first()
    return {"session_id": daily.id, "quiz_date": daily.quiz_date.isoformat(), "completed": daily.completed_at is not None,
            "score": correct, "total": len(rows), "accuracy": round(correct * 100 / len(answered_members), 1) if answered_members else None,
            "answered": len(answered_members), "questions": result_questions, "reward": _reward_payload(reward) if reward else None}


def _finalize_daily_quiz(user, daily, now=None):
    if daily.completed_at:
        return _daily_result(user.id, daily)
    now = _utc(now or datetime.now(timezone.utc))
    members = (db.session.query(PracticeSessionQuestion, Question).join(Question, Question.id == PracticeSessionQuestion.question_id)
               .filter(PracticeSessionQuestion.session_id == daily.id).order_by(PracticeSessionQuestion.position).all())
    correct = answered = 0
    for member, question in members:
        selected = member.selected_option
        is_correct = selected is not None and selected == question.correct_option
        correct += int(is_correct)
        answered += int(selected is not None)
        attempt = PracticeAttempt.query.filter_by(user_id=user.id, session_id=daily.id, question_id=question.id).first()
        if attempt is None:
            attempt = PracticeAttempt(user_id=user.id, session_id=daily.id, question_id=question.id,
                subject=question.subject, topic=question.topic, difficulty=question.difficulty,
                selected_option=selected, is_correct=is_correct, attempted_at=now)
            db.session.add(attempt)
        else:
            attempt.selected_option, attempt.is_correct, attempt.attempted_at = selected, is_correct, now
    daily.completed_at = now
    reward = award_activity(user.id, "practice", daily.id, correct, len(members), topic="Daily Quiz", answered=answered, now=now)
    from ..services.learning import missions_payload
    missions_payload(user.id, now=now)
    db.session.commit()
    payload = _daily_result(user.id, daily)
    payload["reward"] = reward
    return payload


@hub_bp.get("/daily-quiz")
def get_daily_quiz():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    try:
        now = datetime.now(timezone.utc)
        daily = _daily_quiz_session(user.id, now)
        deadline = _deadline(daily.quiz_date)
        if not daily.completed_at and now >= deadline:
            result = _finalize_daily_quiz(user, daily, now)
            return jsonify(quiz=result, deadline_at=deadline.isoformat(), seconds_remaining=0)
        db.session.commit()
        result = _daily_result(user.id, daily)
        result["questions"] = [{**item, "correct_option": None, "explanation": None} for item in result["questions"]] if not daily.completed_at else result["questions"]
        return jsonify(quiz=result, deadline_at=deadline.isoformat(), seconds_remaining=max(0, int((deadline - now).total_seconds())))
    except ValueError as error:
        db.session.rollback()
        return jsonify(error=str(error)), 503


@hub_bp.post("/daily-quiz/<int:session_id>/answer")
def save_daily_answer(session_id):
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    daily = PracticeSession.query.filter_by(id=session_id, user_id=user.id, mode="daily_quiz").first()
    if not daily:
        return jsonify(error="Daily quiz not found."), 404
    now = datetime.now(timezone.utc)
    if daily.completed_at:
        return jsonify(error="This daily quiz is already complete."), 409
    if now >= _deadline(daily.quiz_date):
        result = _finalize_daily_quiz(user, daily, now)
        return jsonify(error="The daily quiz deadline has passed.", result=result), 409
    data = request.get_json(silent=True) or {}
    question_id, selected = data.get("question_id"), data.get("selected_option")
    if not isinstance(question_id, int) or isinstance(question_id, bool) or not isinstance(selected, int) or isinstance(selected, bool) or selected not in range(4):
        return jsonify(error="Choose one of the four answers."), 400
    member = PracticeSessionQuestion.query.filter_by(session_id=daily.id, question_id=question_id).first()
    if not member:
        return jsonify(error="That question is not part of this daily quiz."), 404
    question = db.session.get(Question, question_id)
    member.selected_option, member.is_correct, member.answered_at = selected, selected == question.correct_option, now
    db.session.commit()
    return jsonify(saved=True)


@hub_bp.post("/daily-quiz/<int:session_id>/submit")
def submit_daily_quiz(session_id):
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    daily = PracticeSession.query.filter_by(id=session_id, user_id=user.id, mode="daily_quiz").first()
    if not daily:
        return jsonify(error="Daily quiz not found."), 404
    return jsonify(result=_finalize_daily_quiz(user, daily))

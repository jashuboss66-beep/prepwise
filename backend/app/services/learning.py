from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from ..extensions import db
from ..models import (
    AssessmentAttempt, AssessmentAnswer, DailyLearningPlan, DailyPlanTask,
    LearningMission, LearningNotification, PracticeAttempt,
    PracticeSession, PracticeSessionQuestion, StudentProfile, TargetCompanyPreference,
)
from .adaptive import TOPICS, mastery_snapshot


def notify(user_id, dedupe_key, kind, title, message, now=None):
    row = LearningNotification.query.filter_by(user_id=user_id, dedupe_key=dedupe_key).first()
    if row:
        return row
    row = LearningNotification(user_id=user_id, dedupe_key=dedupe_key, kind=kind, title=title, message=message,
                               created_at=now or datetime.now(timezone.utc))
    db.session.add(row)
    db.session.flush()
    return row


def _profile(user_id):
    row = StudentProfile.query.filter_by(user_id=user_id).first()
    if row is None:
        row = StudentProfile(user_id=user_id)
        db.session.add(row)
        db.session.flush()
    return row


def profile_payload(user_id):
    row = _profile(user_id)
    companies = [item.company_name for item in TargetCompanyPreference.query.filter_by(user_id=user_id).order_by(TargetCompanyPreference.id).all()]
    return {"college": row.college or "", "degree": row.degree or "", "department": row.department or "",
            "graduation_year": row.graduation_year, "cgpa": row.cgpa,
            "technical_skills": row.technical_skills or [], "programming_languages": row.programming_languages or [],
            "preferred_language": row.preferred_language or "", "target_companies": companies,
            "target_roles": row.target_roles or [], "daily_study_target": row.daily_study_target,
            "weekly_study_target": row.weekly_study_target}


def _actual_activity(user_id, start_date, end_date):
    """Return actual minutes, answered questions, sessions, and active study dates."""
    sessions = PracticeSession.query.filter_by(user_id=user_id).filter(
        PracticeSession.completed_at.isnot(None)).all()
    completed_sessions = []
    completed_assessments = []
    minutes_by_day = defaultdict(int)
    answers_by_day = defaultdict(int)
    for row in sessions:
        day = row.completed_at.date()
        if not start_date <= day <= end_date:
            continue
        answered = PracticeAttempt.query.filter_by(session_id=row.id).filter(PracticeAttempt.selected_option.isnot(None)).count()
        total = PracticeSessionQuestion.query.filter_by(session_id=row.id).count()
        if total == 0 or answered < max(1, (total + 1) // 2):
            continue
        estimate = min(60, answered * 2)
        completed_sessions.append(row)
        minutes_by_day[day] += estimate
        answers_by_day[day] += answered
    assessments = AssessmentAttempt.query.filter_by(user_id=user_id).filter(AssessmentAttempt.completed_at.isnot(None)).all()
    for row in assessments:
        day = row.completed_at.date()
        if not start_date <= day <= end_date:
            continue
        answered = AssessmentAnswer.query.filter_by(attempt_id=row.id).filter(AssessmentAnswer.selected_option.isnot(None)).count()
        if answered < max(1, ((row.total_questions or 0) + 1) // 2):
            continue
        # SQLite returns UTC timestamps without tzinfo; normalize both sides before subtracting.
        completed_at = row.completed_at.replace(tzinfo=None)
        started_at = row.started_at.replace(tzinfo=None)
        elapsed_seconds = max(0, (completed_at - started_at).total_seconds())
        estimated_minutes = round(elapsed_seconds / 60) or min(120, answered * 2)
        minutes_by_day[day] += min(120, estimated_minutes)
        answers_by_day[day] += answered
        completed_assessments.append(row)
    return {"sessions": completed_sessions, "assessments": completed_assessments, "minutes_by_day": dict(minutes_by_day),
            "answers_by_day": dict(answers_by_day), "active_days": set(minutes_by_day) | set(answers_by_day)}


def _plan_task(row):
    return {"id": row.id, "subject": row.subject, "topic": row.topic, "activity": row.activity,
            "difficulty": row.difficulty, "duration_minutes": row.duration_minutes,
            "priority": row.priority, "status": row.status, "completed_at": row.completed_at.isoformat() if row.completed_at else None}


def get_or_create_plan(user_id, today=None):
    today = today or datetime.now(timezone.utc).date()
    plan = DailyLearningPlan.query.filter_by(user_id=user_id, plan_date=today).first()
    if plan is None:
        # Surface a missed-goal notice once the prior date is no longer current.
        yesterday = today - timedelta(days=1)
        previous = StudentProfile.query.filter_by(user_id=user_id).first()
        if previous:
            actual = _actual_activity(user_id, yesterday, yesterday)
            actual_minutes = sum(actual["minutes_by_day"].values())
            if actual_minutes < previous.daily_study_target:
                notify(user_id, f"goal-missed-{yesterday.isoformat()}", "goal_missed", "Daily study goal missed",
                       f"You recorded {actual_minutes} of {previous.daily_study_target} study minutes yesterday. Set a fresh target for today.")
        student_profile = _profile(user_id)
        role = (student_profile.target_roles or [None])[0]
        summary = (f"A focused plan for your {role} goal, based on saved performance and your study target."
                   if role else "A focused plan built from your saved performance and study target.")
        plan = DailyLearningPlan(user_id=user_id, plan_date=today, summary=summary)
        db.session.add(plan)
        db.session.flush()
        progress = mastery_snapshot(user_id)
        previous_tasks = (DailyPlanTask.query.join(DailyLearningPlan, DailyPlanTask.plan_id == DailyLearningPlan.id)
                          .filter(DailyLearningPlan.user_id == user_id, DailyLearningPlan.plan_date < today,
                                  DailyPlanTask.status == "pending")
                          .order_by(DailyLearningPlan.plan_date.desc(), DailyPlanTask.id).limit(2).all())
        tasks = []
        task_limit = min(4, max(1, (student_profile.daily_study_target + 29) // 30))
        for prior in previous_tasks:
            if len(tasks) >= task_limit:
                break
            tasks.append({"subject": prior.subject, "topic": prior.topic, "activity": prior.activity,
                          "difficulty": prior.difficulty, "duration": prior.duration_minutes, "priority": "High"})
        for item in progress["recommendations"]:
            if len(tasks) >= task_limit:
                break
            subject, topic, accuracy = item["subject"], item["topic"], item.get("accuracy")
            key = (subject, topic)
            if any((task["subject"], task["topic"]) == key for task in tasks):
                continue
            difficulty = "easy" if accuracy is None or accuracy < 40 else "medium" if accuracy < 75 else "hard"
            activity = (f"Complete a focused technical practice session on {topic}." if subject == "Technical"
                        else f"Solve five {topic} questions and review each explanation.")
            tasks.append({"subject": subject, "topic": topic, "activity": activity, "difficulty": difficulty,
                          "duration": 20 if difficulty == "easy" else 25, "priority": "High" if accuracy is None or accuracy < 50 else "Medium"})
        if not tasks:
            subject = next(iter(TOPICS))
            topic = TOPICS[subject][0]
            tasks.append({"subject": subject, "topic": topic, "activity": f"Start a short {topic} practice set to establish your baseline.",
                          "difficulty": "easy", "duration": 15, "priority": "Getting started"})
        duration_per_task = max(10, round(student_profile.daily_study_target / len(tasks) / 5) * 5)
        for item in tasks:
            db.session.add(DailyPlanTask(plan_id=plan.id, subject=item["subject"], topic=item["topic"],
                activity=item["activity"], difficulty=item["difficulty"], duration_minutes=duration_per_task, priority=item["priority"]))
        notify(user_id, f"daily-plan-{today.isoformat()}", "daily_plan", "Your daily learning plan is ready",
               "Your plan is based on saved results, recent practice, and any unfinished topics.")
        db.session.flush()
    tasks = DailyPlanTask.query.filter_by(plan_id=plan.id).order_by(DailyPlanTask.id).all()
    return {"id": plan.id, "date": plan.plan_date.isoformat(), "summary": plan.summary,
            "tasks": [_plan_task(row) for row in tasks], "duration_minutes": sum(row.duration_minutes for row in tasks)}


def complete_plan_task(user_id, task_id, now=None):
    row = (DailyPlanTask.query.join(DailyLearningPlan, DailyPlanTask.plan_id == DailyLearningPlan.id)
           .filter(DailyPlanTask.id == task_id, DailyLearningPlan.user_id == user_id).first())
    if not row:
        return None
    if row.status != "completed":
        row.status = "completed"
        row.completed_at = now or datetime.now(timezone.utc)
        db.session.commit()
    else:
        db.session.commit()
    return _plan_task(row)


def _period(now, period):
    day = now.date()
    start = day if period == "daily" else day - timedelta(days=day.weekday())
    end = start + timedelta(days=1 if period == "daily" else 7)
    expiry = datetime.combine(end, time.min, tzinfo=timezone.utc)
    return start, end, expiry


def _mission_specs(user_id, period, start, end):
    mastery = mastery_snapshot(user_id)
    weakest = mastery["recommendations"][0] if mastery["recommendations"] else {"subject": "Aptitude", "topic": "Percentages", "accuracy": None}
    practice_rows = PracticeAttempt.query.filter_by(user_id=user_id).filter(PracticeAttempt.selected_option.isnot(None)).all()
    by_date = defaultdict(lambda: {"questions": 0, "minutes": 0})
    topic_sessions = 0
    technical_sessions = 0
    for attempt in practice_rows:
        day = attempt.attempted_at.date()
        if start <= day < end:
            by_date[day]["questions"] += 1
    actual = _actual_activity(user_id, start, end - timedelta(days=1))
    for day, minutes in actual["minutes_by_day"].items():
        by_date[day]["minutes"] += minutes
    for row in actual["sessions"]:
        if start <= row.completed_at.date() < end:
            if row.topic == weakest["topic"]:
                topic_sessions += 1
            if row.subject == "Technical":
                technical_sessions += 1
    answer_count = sum(item["questions"] for item in by_date.values())
    practice_sessions = sum(start <= row.completed_at.date() < end for row in actual["sessions"])
    daily_quizzes = sum(row.mode == "daily_quiz" for row in actual["sessions"] if start <= row.completed_at.date() < end)
    full_assessments = AssessmentAttempt.query.filter_by(user_id=user_id, assessment_mode="ai", assessment_category="Full placement").filter(
        AssessmentAttempt.completed_at.isnot(None)).all()
    full_assessment_count = sum(start <= row.completed_at.date() < end for row in full_assessments)
    profile = _profile(user_id)
    goal_days = sum(item["minutes"] >= profile.daily_study_target for item in by_date.values())
    if period == "daily":
        historical_topic = [row for row in practice_rows if row.topic == weakest["topic"] and row.attempted_at.date() < start]
        baseline = (sum(int(row.is_correct) for row in historical_topic) * 100 / len(historical_topic)) if historical_topic else None
        accuracy_target = 70 if baseline is None else min(100, max(60, int(baseline) + 10))
        current_topic = [row for row in practice_rows if row.topic == weakest["topic"] and row.attempted_at.date() == start]
        current_accuracy = round(sum(int(row.is_correct) for row in current_topic) * 100 / len(current_topic)) if current_topic else 0
        return [
            ("questions-10", "Complete 10 practice questions", f"Answer ten questions across your practice sessions.", {"metric": "questions"}, 10, answer_count, 15, 5),
            ("weak-topic", f"Practice {weakest['topic']}", f"Complete a practice session for your current priority topic.", {"metric": "topic_sessions", "topic": weakest["topic"]}, 1, int(topic_sessions > 0), 12, 5),
            ("technical-session", "Complete a technical session", "Finish one technical practice session.", {"metric": "technical_sessions"}, 1, int(technical_sessions > 0), 12, 5),
            ("accuracy-improvement", f"Improve {weakest['topic']} accuracy", f"Reach {accuracy_target}% accuracy in today's {weakest['topic']} practice.",
             {"metric": "topic_accuracy", "topic": weakest["topic"], "target_accuracy": accuracy_target,
              "baseline_accuracy": round(baseline, 1) if baseline is not None else None}, accuracy_target, current_accuracy, 15, 6),
            ("daily-goal", "Reach your daily study target", f"Record {profile.daily_study_target} study minutes today.", {"metric": "minutes", "goal": profile.daily_study_target}, profile.daily_study_target, sum(item["minutes"] for item in by_date.values()), 20, 8),
            ("daily-quiz", "Complete today's daily quiz", "Answer at least half of the ten-question placement quiz.", {"metric": "daily_quiz"}, 1, min(1, daily_quizzes), 20, 10),
        ]
    return [
        ("questions-30", "Answer 30 practice questions", "Build steady practice across the week.", {"metric": "questions"}, 30, answer_count, 35, 15),
        ("practice-5", "Complete five practice sessions", "Finish five saved adaptive practice sessions.", {"metric": "sessions"}, 5, practice_sessions, 40, 20),
        ("weak-topic-3", f"Practice {weakest['topic']} three times", "Return to your priority topic in three sessions.", {"metric": "topic_sessions", "topic": weakest["topic"]}, 3, topic_sessions, 35, 15),
        ("goal-days-5", "Meet your daily target five days", "Reach your daily study target on five separate days.", {"metric": "goal_days"}, 5, goal_days, 35, 15),
        ("daily-quizzes-3", "Complete three daily quizzes", "Finish at least half of three different daily placement quizzes.", {"metric": "daily_quizzes"}, 3, daily_quizzes, 40, 20),
        ("full-assessment", "Complete a full placement assessment", "Finish a timed assessment covering all placement categories.", {"metric": "full_assessment"}, 1, min(1, full_assessment_count), 50, 25),
    ]


def _mission_progress(user_id, mission):
    end = mission.period_start + timedelta(days=1 if mission.period == "daily" else 7)
    attempts = PracticeAttempt.query.filter_by(user_id=user_id).filter(PracticeAttempt.selected_option.isnot(None)).all()
    questions = sum(mission.period_start <= row.attempted_at.date() < end for row in attempts)
    actual = _actual_activity(user_id, mission.period_start, end - timedelta(days=1))
    sessions = [row for row in actual["sessions"] if mission.period_start <= row.completed_at.date() < end]
    metric = (mission.requirements or {}).get("metric")
    if metric == "questions":
        return questions
    if metric == "sessions":
        return len(sessions)
    if metric == "daily_quiz":
        return min(1, sum(row.mode == "daily_quiz" for row in sessions))
    if metric == "daily_quizzes":
        return sum(row.mode == "daily_quiz" for row in sessions)
    if metric == "topic_sessions":
        topic = (mission.requirements or {}).get("topic")
        return sum(row.topic == topic for row in sessions)
    if metric == "technical_sessions":
        return sum(row.subject == "Technical" for row in sessions)
    if metric == "topic_accuracy":
        topic = (mission.requirements or {}).get("topic")
        topic_rows = [row for row in attempts if row.topic == topic and row.attempted_at.date() == mission.period_start]
        return round(sum(int(row.is_correct) for row in topic_rows) * 100 / len(topic_rows)) if topic_rows else 0
    if metric == "minutes":
        return sum(actual["minutes_by_day"].values())
    if metric == "goal_days":
        target = _profile(user_id).daily_study_target
        return sum(minutes >= target for minutes in actual["minutes_by_day"].values())
    if metric == "full_assessment":
        attempts = AssessmentAttempt.query.filter_by(user_id=user_id, assessment_mode="ai", assessment_category="Full placement").filter(
            AssessmentAttempt.completed_at.isnot(None)).all()
        return min(1, sum(mission.period_start <= row.completed_at.date() < end for row in attempts))
    return mission.progress


def _award_mission(user_id, mission, now):
    from .gamification import level_details
    from ..models import GamificationProfile, RewardTransaction
    existing = RewardTransaction.query.filter_by(user_id=user_id, activity_type="mission", activity_id=mission.id).first()
    if existing:
        return
    profile = GamificationProfile.query.filter_by(user_id=user_id).first()
    if profile is None:
        profile = GamificationProfile(user_id=user_id)
        db.session.add(profile)
        db.session.flush()
    old_level = level_details(profile.total_xp)["level"]
    profile.total_xp += mission.reward_xp
    profile.total_coins += mission.reward_coins
    new_level = level_details(profile.total_xp)["level"]
    db.session.add(RewardTransaction(user_id=user_id, activity_type="mission", activity_id=mission.id,
        xp_earned=mission.reward_xp, coins_earned=mission.reward_coins, reason=f"Mission completed: {mission.title}",
        achievements=[], level_up=new_level > old_level, created_at=now))
    if new_level > old_level:
        notify(user_id, f"level-up-mission-{mission.id}", "level_up", "Level upgraded",
               f"Mission rewards moved you to level {new_level}.", now)


def _award_daily_completion_bonus(user_id, period_start, now):
    from .gamification import level_details
    from ..models import GamificationProfile, RewardTransaction
    db.session.flush()
    rows = LearningMission.query.filter_by(user_id=user_id, period="daily", period_start=period_start).all()
    if not rows or any(not row.completed for row in rows):
        return
    anchor = min(rows, key=lambda row: row.id)
    if RewardTransaction.query.filter_by(user_id=user_id, activity_type="daily_all", activity_id=anchor.id).first():
        return
    profile = GamificationProfile.query.filter_by(user_id=user_id).first()
    if profile is None:
        from ..models import GamificationProfile as Profile
        profile = Profile(user_id=user_id)
        db.session.add(profile)
        db.session.flush()
    old_level = level_details(profile.total_xp)["level"]
    profile.total_xp += 25
    profile.total_coins += 10
    new_level = level_details(profile.total_xp)["level"]
    db.session.add(RewardTransaction(user_id=user_id, activity_type="daily_all", activity_id=anchor.id,
        xp_earned=25, coins_earned=10, reason="All daily learning challenges completed", achievements=[],
        level_up=new_level > old_level, created_at=now))
    notify(user_id, f"daily-all-{period_start.isoformat()}", "mission_complete", "All daily challenges complete",
           "Bonus reward earned: 25 XP and 10 coins.", now)
    if new_level > old_level:
        notify(user_id, f"level-up-daily-all-{period_start.isoformat()}", "level_up", "Level upgraded",
               f"Daily challenge bonus moved you to level {new_level}.", now)


def missions_payload(user_id, now=None):
    now = now or datetime.now(timezone.utc)
    response = {}
    for period in ("daily", "weekly"):
        start, end, expiry = _period(now, period)
        specs = _mission_specs(user_id, period, start, end)
        for key, title, description, requirements, target, progress, xp, coins in specs:
            mission_key = f"{period}:{key}"
            row = LearningMission.query.filter_by(user_id=user_id, mission_key=mission_key, period_start=start).first()
            if row is None:
                row = LearningMission(user_id=user_id, mission_key=mission_key, period=period, title=title,
                    description=description, requirements=requirements, target=target, progress=progress,
                    reward_xp=xp, reward_coins=coins, period_start=start, expires_at=expiry)
                db.session.add(row)
                db.session.flush()
            elif mission_key == "daily:daily-goal" and not row.completed:
                current_target = _profile(user_id).daily_study_target
                row.title = "Reach your daily study target"
                row.description = f"Record {current_target} study minutes today."
                row.target = current_target
                row.requirements = {"metric": "minutes", "goal": current_target}
            row.progress = min(row.target, _mission_progress(user_id, row))
            if not row.completed and row.progress >= row.target:
                row.completed = True
                row.completed_at = now
                _award_mission(user_id, row, now)
                notify(user_id, f"mission-{row.id}", "mission_complete", "Mission completed", f"{row.title}. Reward: {row.reward_xp} XP and {row.reward_coins} coins.", now)
            if period == "daily":
                _award_daily_completion_bonus(user_id, start, now)
            response.setdefault(period, []).append({"id": row.id, "title": row.title, "description": row.description,
                "requirements": row.requirements, "progress": row.progress, "target": row.target,
                "progress_percent": round(row.progress * 100 / row.target) if row.target else 100,
                "completed": row.completed, "reward_xp": row.reward_xp, "reward_coins": row.reward_coins,
                "expires_at": row.expires_at.isoformat()})
    db.session.commit()
    return response


def goals_payload(user_id, today=None):
    today = today or datetime.now(timezone.utc).date()
    profile = _profile(user_id)
    daily = _actual_activity(user_id, today, today)
    week_start = today - timedelta(days=today.weekday())
    weekly = _actual_activity(user_id, week_start, today)
    daily_minutes = sum(daily["minutes_by_day"].values())
    weekly_minutes = sum(weekly["minutes_by_day"].values())
    daily_met = daily_minutes >= profile.daily_study_target
    history_start = today - timedelta(days=6)
    recent = _actual_activity(user_id, history_start, today)
    history = []
    for offset in range(7):
        day = history_start + timedelta(days=offset)
        minutes = recent["minutes_by_day"].get(day, 0)
        status = "completed" if minutes >= profile.daily_study_target else "in_progress" if day == today else "missed"
        history.append({"date": day.isoformat(), "actual_minutes": minutes,
                        "target_minutes": profile.daily_study_target, "status": status})
    return {"targets": {"daily_minutes": profile.daily_study_target, "weekly_minutes": profile.weekly_study_target},
            "today": {"date": today.isoformat(), "minutes": daily_minutes,
                      "completed_activities": len(daily["sessions"]) + len(daily["assessments"]),
                      "target_met": daily_met, "missed": daily_minutes < profile.daily_study_target and today < datetime.now(timezone.utc).date()},
            "week": {"start": week_start.isoformat(), "minutes": weekly_minutes,
                     "completed_activities": len(weekly["sessions"]) + len(weekly["assessments"]), "active_days": len(weekly["active_days"]),
                     "target_met": weekly_minutes >= profile.weekly_study_target},
            "daily_history": history,
            "completed_goals": sum(row["status"] == "completed" for row in history),
            "missed_goals": sum(row["status"] == "missed" for row in history),
            "daily_progress_percent": min(100, round(daily_minutes * 100 / max(1, profile.daily_study_target))),
            "weekly_progress_percent": min(100, round(weekly_minutes * 100 / max(1, profile.weekly_study_target)))}


def notifications_payload(user_id):
    rows = LearningNotification.query.filter_by(user_id=user_id).order_by(LearningNotification.created_at.desc(), LearningNotification.id.desc()).limit(50).all()
    return [{"id": row.id, "kind": row.kind, "title": row.title, "message": row.message,
             "created_at": row.created_at.isoformat(), "read": row.read_at is not None} for row in rows]

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func

from ..extensions import db
from ..models import (
    AchievementUnlock, AssessmentAnswer, AssessmentAttempt, GamificationProfile,
    LearningActivityDay, PracticeAttempt, PracticeSession, RewardTransaction,
    User,
)

XP_PER_LEVEL = 100
ACHIEVEMENTS = [
    {"key": "first_assessment", "name": "First Assessment", "description": "Complete your first placement assessment.", "icon": "📝", "coins": 10},
    {"key": "first_practice", "name": "Practice Starter", "description": "Complete your first adaptive practice session.", "icon": "🎯", "coins": 5},
    {"key": "perfect_score", "name": "Perfect Score", "description": "Earn 100% on an assessment or practice session.", "icon": "💯", "coins": 20},
    {"key": "hundred_questions", "name": "Century Solver", "description": "Submit answers to 100 assessment and practice questions.", "icon": "⚡", "coins": 50},
    {"key": "seven_day_streak", "name": "Seven-Day Streak", "description": "Practice on seven consecutive days.", "icon": "🔥", "coins": 50},
    {"key": "consistent_learner", "name": "Consistent Learner", "description": "Learn on five different days.", "icon": "📅", "coins": 25},
    {"key": "topic_master", "name": "Topic Master", "description": "Reach 80% accuracy across at least five attempts in a topic.", "icon": "🏆", "coins": 15},
]
ACHIEVEMENT_BY_KEY = {item["key"]: item for item in ACHIEVEMENTS}


def level_details(total_xp):
    level = total_xp // XP_PER_LEVEL + 1
    current_level_xp = total_xp % XP_PER_LEVEL
    return {"level": level, "current_level_xp": current_level_xp,
            "next_level_xp": XP_PER_LEVEL, "progress_percent": current_level_xp}


def _profile(user_id):
    profile = GamificationProfile.query.filter_by(user_id=user_id).first()
    if profile is None:
        profile = GamificationProfile(user_id=user_id)
        db.session.add(profile)
        db.session.flush()
    return profile


def _unlock_achievements(user_id, activity_type, activity_id, accuracy, topic, profile, active_days):
    db.session.flush()
    completed_assessments = AssessmentAttempt.query.filter_by(user_id=user_id).filter(AssessmentAttempt.completed_at.isnot(None)).count()
    completed_practice = PracticeSession.query.filter_by(user_id=user_id).filter(PracticeSession.completed_at.isnot(None)).count()
    answered_assessment = (db.session.query(func.count(AssessmentAnswer.id)).join(
        AssessmentAttempt, AssessmentAttempt.id == AssessmentAnswer.attempt_id
    ).filter(AssessmentAttempt.user_id == user_id, AssessmentAttempt.completed_at.isnot(None),
             AssessmentAnswer.selected_option.isnot(None)).scalar() or 0)
    answered_practice = PracticeAttempt.query.filter_by(user_id=user_id).filter(PracticeAttempt.selected_option.isnot(None)).count()
    topic_master = False
    if topic:
        attempts = PracticeAttempt.query.filter_by(user_id=user_id, topic=topic).filter(PracticeAttempt.selected_option.isnot(None)).all()
        topic_master = len(attempts) >= 5 and sum(int(item.is_correct) for item in attempts) / len(attempts) >= .8
    checks = {
        "first_assessment": completed_assessments >= 1,
        "first_practice": completed_practice >= 1,
        "perfect_score": accuracy == 100,
        "hundred_questions": answered_assessment + answered_practice >= 100,
        "seven_day_streak": profile.current_streak >= 7,
        "consistent_learner": active_days >= 5,
        "topic_master": topic_master,
    }
    existing = {row.achievement_key for row in AchievementUnlock.query.filter_by(user_id=user_id).all()}
    newly_unlocked = []
    bonus_coins = 0
    for key, met in checks.items():
        if met and key not in existing:
            db.session.add(AchievementUnlock(user_id=user_id, achievement_key=key))
            newly_unlocked.append(key)
            bonus_coins += ACHIEVEMENT_BY_KEY[key]["coins"]
    db.session.flush()
    return newly_unlocked, bonus_coins


def award_activity(user_id, activity_type, activity_id, correct, total, topic=None, now=None, answered=None):
    """Calculate and persist an activity's rewards in the caller's transaction."""
    existing = RewardTransaction.query.filter_by(user_id=user_id, activity_type=activity_type, activity_id=activity_id).first()
    if existing:
        return _reward_payload(existing, duplicate=True)
    now = now or datetime.now(timezone.utc)
    correct = max(0, int(correct or 0))
    total = max(0, int(total or 0))
    answered = total if answered is None else max(0, int(answered))
    if total == 0 or answered < max(1, (total + 1) // 2):
        return None
    activity_day = now.date()
    profile = _profile(user_id)
    day_row = LearningActivityDay.query.filter_by(user_id=user_id, activity_date=activity_day).first()
    if day_row:
        day_row.activity_count += 1
    else:
        db.session.add(LearningActivityDay(user_id=user_id, activity_date=activity_day, activity_count=1))
        if profile.last_activity_date is None:
            profile.current_streak = 1
        elif profile.last_activity_date == activity_day:
            pass
        elif profile.last_activity_date == activity_day - timedelta(days=1):
            profile.current_streak += 1
        else:
            profile.current_streak = 1
        profile.longest_streak = max(profile.longest_streak, profile.current_streak)
        profile.last_activity_date = activity_day
    db.session.flush()
    active_days = LearningActivityDay.query.filter_by(user_id=user_id).count()

    accuracy = (correct * 100 / total) if total else 0
    if activity_type == "assessment":
        xp = 50 + correct * 2 + (20 if accuracy >= 80 else 0) + (30 if accuracy == 100 else 0)
        base_coins = 5
        reason = f"Assessment completed ({correct}/{total} correct)"
    elif activity_type == "coding_problem":
        xp = 40 + (20 if accuracy == 100 else 0)
        base_coins = 5
        reason = "First accepted coding solution"
    else:
        xp = 10 + correct * 5 + (10 if accuracy >= 80 else 0)
        base_coins = 2
        reason = f"Practice session completed ({correct}/{total} correct)"
    unlocked, bonus_coins = _unlock_achievements(user_id, activity_type, activity_id, accuracy, topic, profile, active_days)
    from .learning import notify
    for key in unlocked:
        achievement = ACHIEVEMENT_BY_KEY[key]
        notify(user_id, f"achievement-{key}", "achievement", f"Achievement unlocked: {achievement['name']}", achievement["description"], now)
    old_level = level_details(profile.total_xp)["level"]
    earned_coins = base_coins + bonus_coins
    profile.total_xp += xp
    profile.total_coins += earned_coins
    new_level = level_details(profile.total_xp)["level"]
    if new_level > old_level:
        notify(user_id, f"level-up-{activity_type}-{activity_id}", "level_up", "Level upgraded",
               f"You reached level {new_level}. Keep building your placement skills.", now)
    if profile.current_streak in (3, 7, 14, 30) and profile.last_activity_date == activity_day:
        notify(user_id, f"streak-{profile.current_streak}-{activity_day.isoformat()}", "streak", f"{profile.current_streak}-day learning streak",
               "Your saved learning activity shows consistent progress. Keep it going!", now)
    transaction = RewardTransaction(user_id=user_id, activity_type=activity_type, activity_id=activity_id,
        xp_earned=xp, coins_earned=earned_coins, reason=reason, achievements=unlocked, level_up=new_level > old_level,
        created_at=now)
    db.session.add(transaction)
    db.session.flush()
    return _reward_payload(transaction)


def _reward_payload(transaction, duplicate=False):
    return {"id": transaction.id, "xp_earned": transaction.xp_earned, "coins_earned": transaction.coins_earned,
            "reason": transaction.reason, "achievements_unlocked": transaction.achievements or [],
            "level_up": transaction.level_up, "duplicate": duplicate}


def gamification_dashboard(user_id):
    profile = GamificationProfile.query.filter_by(user_id=user_id).first()
    if profile is None:
        profile = GamificationProfile(user_id=user_id, total_xp=0, total_coins=0, current_streak=0, longest_streak=0)
    unlocked_rows = AchievementUnlock.query.filter_by(user_id=user_id).all()
    unlocked = {row.achievement_key: row.unlocked_at for row in unlocked_rows}
    rewards = RewardTransaction.query.filter_by(user_id=user_id).order_by(RewardTransaction.created_at.desc(), RewardTransaction.id.desc()).limit(20).all()
    leaderboard_rows = (db.session.query(User.name, GamificationProfile.total_xp)
        .outerjoin(GamificationProfile, GamificationProfile.user_id == User.id)
        .order_by(GamificationProfile.total_xp.desc().nullslast(), User.name.asc()).limit(20).all())
    leaderboard = [{"name": name, "xp": xp or 0, **level_details(xp or 0)} for name, xp in leaderboard_rows]
    return {"profile": {"total_xp": profile.total_xp, "total_coins": profile.total_coins,
                         "current_streak": profile.current_streak, "longest_streak": profile.longest_streak,
                         "last_activity_date": profile.last_activity_date.isoformat() if profile.last_activity_date else None,
                         **level_details(profile.total_xp)},
            "achievements": [{**item, "unlocked": item["key"] in unlocked,
                              "unlocked_at": unlocked[item["key"]].isoformat() if item["key"] in unlocked else None}
                             for item in ACHIEVEMENTS],
            "recent_rewards": [{**_reward_payload(row), "created_at": row.created_at.isoformat()} for row in rewards],
            "leaderboard": leaderboard}

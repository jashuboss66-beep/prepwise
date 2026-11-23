from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "email": self.email}


class StudentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True, index=True)
    college = db.Column(db.String(160))
    degree = db.Column(db.String(100))
    department = db.Column(db.String(100))
    graduation_year = db.Column(db.Integer)
    cgpa = db.Column(db.Float)
    technical_skills = db.Column(db.JSON, nullable=False, default=list)
    programming_languages = db.Column(db.JSON, nullable=False, default=list)
    preferred_language = db.Column(db.String(60))
    target_roles = db.Column(db.JSON, nullable=False, default=list)
    daily_study_target = db.Column(db.Integer, nullable=False, default=60)
    weekly_study_target = db.Column(db.Integer, nullable=False, default=420)
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class DailyLearningPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    plan_date = db.Column(db.Date, nullable=False, index=True)
    summary = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint("user_id", "plan_date", name="uq_daily_plan_user_date"),)


class DailyPlanTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("daily_learning_plan.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = db.Column(db.String(40), nullable=False)
    topic = db.Column(db.String(80), nullable=False)
    activity = db.Column(db.String(220), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    completed_at = db.Column(db.DateTime)


class LearningMission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    mission_key = db.Column(db.String(80), nullable=False)
    period = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    requirements = db.Column(db.JSON, nullable=False)
    progress = db.Column(db.Integer, nullable=False, default=0)
    target = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    reward_xp = db.Column(db.Integer, nullable=False)
    reward_coins = db.Column(db.Integer, nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    completed_at = db.Column(db.DateTime)
    __table_args__ = (db.UniqueConstraint("user_id", "mission_key", "period_start", name="uq_user_mission_period"),)


class LearningNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    dedupe_key = db.Column(db.String(140), nullable=False)
    kind = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    read_at = db.Column(db.DateTime)
    __table_args__ = (db.UniqueConstraint("user_id", "dedupe_key", name="uq_user_notification_key"),)


class GamificationProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True, index=True)
    total_xp = db.Column(db.Integer, nullable=False, default=0)
    total_coins = db.Column(db.Integer, nullable=False, default=0)
    current_streak = db.Column(db.Integer, nullable=False, default=0)
    longest_streak = db.Column(db.Integer, nullable=False, default=0)
    last_activity_date = db.Column(db.Date)


class LearningActivityDay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    activity_date = db.Column(db.Date, nullable=False)
    activity_count = db.Column(db.Integer, nullable=False, default=1)
    __table_args__ = (db.UniqueConstraint("user_id", "activity_date", name="uq_user_learning_day"),)


class RewardTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    activity_type = db.Column(db.String(30), nullable=False)
    activity_id = db.Column(db.Integer, nullable=False)
    xp_earned = db.Column(db.Integer, nullable=False)
    coins_earned = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(160), nullable=False)
    achievements = db.Column(db.JSON, nullable=False, default=list)
    level_up = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    __table_args__ = (db.UniqueConstraint("user_id", "activity_type", "activity_id", name="uq_reward_activity"),)


class AchievementUnlock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    achievement_key = db.Column(db.String(50), nullable=False)
    unlocked_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint("user_id", "achievement_key", name="uq_user_achievement"),)


class TargetCompanyPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    company_name = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint("user_id", "company_name", name="uq_user_target_company"),)


class PlacementReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    data_snapshot = db.Column(db.JSON, nullable=False)
    narrative = db.Column(db.JSON, nullable=False)
    source = db.Column(db.String(20), nullable=False, default="fallback")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(40), nullable=False, index=True)
    prompt = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(80), nullable=False, default="General")
    difficulty = db.Column(db.String(20), nullable=False, default="medium")
    practice_only = db.Column(db.Boolean, nullable=False, default=False)
    category = db.Column(db.String(40), nullable=False, default="Legacy")
    source = db.Column(db.String(120), nullable=False, default="Original: Prepwise project")
    license = db.Column(db.String(120), nullable=False, default="Project original content")
    reference_url = db.Column(db.String(500))


class QuestionBookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint("user_id", "question_id", name="uq_user_question_bookmark"),)


class PracticeSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    subject = db.Column(db.String(40), nullable=False)
    topic = db.Column(db.String(80))
    started_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    mode = db.Column(db.String(20), nullable=False, default="normal")
    quiz_date = db.Column(db.Date)


class PracticeSessionQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("practice_session.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    selected_option = db.Column(db.Integer)
    is_correct = db.Column(db.Boolean)
    answered_at = db.Column(db.DateTime)
    __table_args__ = (db.UniqueConstraint("session_id", "question_id", name="uq_practice_session_question"),)


class PracticeAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey("practice_session.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False, index=True)
    subject = db.Column(db.String(40), nullable=False, index=True)
    topic = db.Column(db.String(80), nullable=False, index=True)
    difficulty = db.Column(db.String(20), nullable=False)
    selected_option = db.Column(db.Integer)
    is_correct = db.Column(db.Boolean, nullable=False)
    attempted_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


class CodingSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    problem_id = db.Column(db.String(60), nullable=False, index=True)
    language = db.Column(db.String(30), nullable=False, default="python")
    source_code = db.Column(db.Text, nullable=False)
    passed_tests = db.Column(db.Integer, nullable=False, default=0)
    total_tests = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), nullable=False)
    execution_time = db.Column(db.Float)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


class AssessmentAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    duration_seconds = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime)
    correct_answers = db.Column(db.Integer)
    total_questions = db.Column(db.Integer, nullable=False)
    score_percent = db.Column(db.Float)
    assessment_mode = db.Column(db.String(20), nullable=False, default="initial")
    assessment_category = db.Column(db.String(40))
    difficulty = db.Column(db.String(20))


class AssessmentAttemptQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("assessment_attempt.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    option_order = db.Column(db.JSON, nullable=False, default=lambda: [0, 1, 2, 3])
    first_viewed_at = db.Column(db.DateTime)
    __table_args__ = (
        db.UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
        db.UniqueConstraint("attempt_id", "position", name="uq_attempt_position"),
    )


class AssessmentAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("assessment_attempt.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    selected_option = db.Column(db.Integer)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    answered_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    time_spent_seconds = db.Column(db.Integer)
    __table_args__ = (db.UniqueConstraint("attempt_id", "question_id", name="uq_attempt_answer"),)


class AssessmentSubjectResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("assessment_attempt.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = db.Column(db.String(40), nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    score_percent = db.Column(db.Float, nullable=False)
    insight = db.Column(db.String(30), nullable=False)
    __table_args__ = (db.UniqueConstraint("attempt_id", "subject", name="uq_attempt_subject_result"),)


class AIAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("assessment_attempt.id"), nullable=False, index=True)
    content = db.Column(db.JSON, nullable=False)
    source = db.Column(db.String(20), nullable=False, default="fallback")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class AIChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False, default="New conversation")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), index=True)


class AIChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("ai_chat_session.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(20), nullable=False, default="user")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class AIPracticeQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    subject = db.Column(db.String(40), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

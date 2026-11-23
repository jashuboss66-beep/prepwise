import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from app import create_app
from app.extensions import db
from app.models import (AchievementUnlock, AssessmentAttemptQuestion, GamificationProfile, PracticeAttempt,
                        PracticeSession, Question, RewardTransaction)
from app.services.gamification import award_activity, level_details

class GamificationTests(unittest.TestCase):
    def setUp(self):
        folder = Path(__file__).resolve().parents[1] / "instance"; folder.mkdir(exist_ok=True)
        self.path = folder / f"phase5-{uuid4().hex}.sqlite3"
        self.config = {"TESTING": True, "SECRET_KEY": "phase5", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.path.as_posix()}"}
        self.app = create_app(self.config); self.context = self.app.app_context(); self.context.push()
        self.one, self.two = self.app.test_client(), self.app.test_client()
        self.one.post("/api/auth/register", json={"name":"Avery Learner","email":"avery@test.local","password":"password123"})
        self.two.post("/api/auth/register", json={"name":"Blake Learner","email":"blake@test.local","password":"password123"})

    def tearDown(self):
        db.session.remove(); db.engine.dispose(); self.context.pop()
        for suffix in ("", "-journal", "-wal", "-shm"):
            Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def complete_assessment(self, perfect=True):
        attempt_id = self.one.post("/api/assessments").json["attempt_id"]
        members = AssessmentAttemptQuestion.query.filter_by(attempt_id=attempt_id).order_by(AssessmentAttemptQuestion.position).all()
        for index, member in enumerate(members):
            q = db.session.get(Question, member.question_id)
            selected = q.correct_option if perfect or index < 8 else (q.correct_option + 1) % 4
            self.one.put(f"/api/assessments/{attempt_id}/answers", json={"question_id":q.id,"selected_option":selected})
        return attempt_id

    def test_activity_rewards_duplicates_level_achievements_and_persistence(self):
        attempt_id = self.complete_assessment()
        result = self.one.post(f"/api/assessments/{attempt_id}/submit").json
        self.assertEqual(result["reward"]["xp_earned"], 140)
        self.assertEqual(result["reward"]["coins_earned"], 35)
        self.assertTrue(result["reward"]["level_up"])
        self.assertEqual(set(result["reward"]["achievements_unlocked"]), {"first_assessment", "perfect_score"})
        self.one.post(f"/api/assessments/{attempt_id}/submit")
        self.assertEqual(RewardTransaction.query.filter_by(activity_type="assessment", activity_id=attempt_id).count(), 1)
        dash = self.one.get("/api/gamification").json
        self.assertEqual(dash["profile"]["level"], 2)
        self.assertEqual(dash["profile"]["total_xp"], 140)
        self.assertEqual(dash["profile"]["current_streak"], 1)
        self.assertEqual(dash["leaderboard"][0]["name"], "Avery Learner")
        self.assertNotIn("email", dash["leaderboard"][0])
        self.assertEqual(self.two.get("/api/gamification").json["profile"]["total_xp"], 0)
        db.session.remove()
        self.assertEqual(self.one.get("/api/gamification").json["profile"]["total_xp"], 140)

    def test_practice_rewards_are_integrated_and_award_only_once(self):
        session = self.one.post("/api/practice/sessions", json={"subject":"Aptitude"}).json["session"]
        answers=[]
        for item in session["questions"]:
            question = db.session.get(Question, item["id"])
            answers.append({"question_id":question.id,"selected_option":question.correct_option})
        response = self.one.post(f"/api/practice/sessions/{session['id']}/submit", json={"answers":answers})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["reward"]["xp_earned"], 45)  # 10 base + 5 per correct + 10 high accuracy
        self.assertIn("first_practice", response.json["reward"]["achievements_unlocked"])
        self.assertEqual(self.one.post(f"/api/practice/sessions/{session['id']}/submit", json={"answers":answers}).status_code, 409)
        self.assertEqual(RewardTransaction.query.filter_by(activity_type="practice", activity_id=session["id"]).count(), 1)
        self.assertEqual(PracticeAttempt.query.filter_by(session_id=session["id"]).count(), len(answers))

    def test_streak_same_day_gap_consistency_and_seven_day_badge(self):
        user_id = 1
        start = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
        award_activity(user_id, "practice", 101, 0, 1, now=start)
        award_activity(user_id, "practice", 102, 0, 1, now=start + timedelta(hours=2))
        profile = GamificationProfile.query.filter_by(user_id=user_id).first()
        self.assertEqual(profile.current_streak, 1)
        self.assertEqual(profile.longest_streak, 1)
        award_activity(user_id, "practice", 103, 0, 1, now=start + timedelta(days=1))
        self.assertEqual(profile.current_streak, 2)
        award_activity(user_id, "practice", 104, 0, 1, now=start + timedelta(days=3))
        self.assertEqual(profile.current_streak, 1)
        self.assertEqual(profile.longest_streak, 2)
        # Seven consecutive learning dates unlock the streak achievement exactly once.
        for day in range(4, 10):
            award_activity(user_id, "practice", 200 + day, 0, 1, now=start + timedelta(days=day))
        self.assertEqual(profile.current_streak, 7)
        self.assertEqual(profile.longest_streak, 7)
        self.assertEqual(AchievementUnlock.query.filter_by(user_id=user_id, achievement_key="seven_day_streak").count(), 1)
        self.assertEqual(AchievementUnlock.query.filter_by(user_id=user_id, achievement_key="consistent_learner").count(), 1)

    def test_level_thresholds_and_read_only_reward_endpoint(self):
        self.assertEqual(level_details(0)["level"], 1)
        self.assertEqual(level_details(99)["progress_percent"], 99)
        self.assertEqual(level_details(100)["level"], 2)
        self.assertEqual(self.two.post("/api/gamification", json={"xp":999999,"coins":999999}).status_code, 405)
        self.assertEqual(self.app.test_client().get("/api/gamification").status_code, 401)

    def test_empty_submissions_do_not_create_rewards_or_streaks(self):
        attempt = self.one.post("/api/assessments").json["attempt_id"]
        assessment_result = self.one.post(f"/api/assessments/{attempt}/submit").json
        self.assertIsNone(assessment_result["reward"])
        session = self.one.post("/api/practice/sessions", json={"subject":"Technical"}).json["session"]
        blank_answers = [{"question_id":item["id"],"selected_option":None} for item in session["questions"]]
        practice_result = self.one.post(f"/api/practice/sessions/{session['id']}/submit", json={"answers":blank_answers}).json
        self.assertIsNone(practice_result["reward"])
        self.assertEqual(RewardTransaction.query.count(), 0)
        self.assertIsNone(GamificationProfile.query.filter_by(user_id=1).first())

    def test_question_milestone_and_topic_master_badges(self):
        questions = Question.query.filter_by(subject="Aptitude", topic="Percentages").all()
        session = PracticeSession(user_id=1, subject="Aptitude", topic="Percentages",
                                  started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc))
        db.session.add(session); db.session.flush()
        attempts = []
        for index in range(100):
            question = questions[index % len(questions)]
            attempts.append(PracticeAttempt(user_id=1, session_id=session.id, question_id=question.id,
                subject="Aptitude", topic="Percentages", difficulty=question.difficulty,
                selected_option=question.correct_option, is_correct=True))
        db.session.add_all(attempts); db.session.flush()
        reward = award_activity(1, "practice", session.id, 5, 5, topic="Percentages")
        self.assertIn("hundred_questions", reward["achievements_unlocked"])
        self.assertIn("topic_master", reward["achievements_unlocked"])
        self.assertEqual(AchievementUnlock.query.filter_by(user_id=1, achievement_key="hundred_questions").count(), 1)

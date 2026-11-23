import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.models import LearningNotification, PracticeAttempt, Question, RewardTransaction


class LearningManagementTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / "instance"
        root.mkdir(exist_ok=True)
        self.path = root / f"batch1-{uuid4().hex}.sqlite3"
        config = {"TESTING": True, "SECRET_KEY": "batch1", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.path.as_posix()}"}
        self.app = create_app(config)
        self.context = self.app.app_context()
        self.context.push()
        self.one, self.two = self.app.test_client(), self.app.test_client()
        self.one.post("/api/auth/register", json={"name": "Morgan Student", "email": "morgan@batch.local", "password": "password123"})
        self.two.post("/api/auth/register", json={"name": "Taylor Student", "email": "taylor@batch.local", "password": "password123"})

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()
        for suffix in ("", "-journal", "-wal", "-shm"):
            Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def practice(self, topic="Percentages", subject="Aptitude", correct=False):
        started = self.one.post("/api/practice/sessions", json={"subject": subject, "topic": topic})
        self.assertEqual(started.status_code, 201)
        questions = started.json["session"]["questions"]
        answers = []
        for item in questions:
            question = db.session.get(Question, item["id"])
            option = question.correct_option if correct else (question.correct_option + 1) % 4
            answers.append({"question_id": question.id, "selected_option": option})
        response = self.one.post(f"/api/practice/sessions/{started.json['session']['id']}/submit", json={"answers": answers})
        self.assertEqual(response.status_code, 200)
        return response

    def test_profile_edit_validation_and_user_isolation(self):
        first = self.one.get("/api/learning/profile").json["profile"]
        self.assertEqual(first["college"], "")
        self.assertEqual(first["daily_study_target"], 60)
        response = self.one.put("/api/learning/profile", json={
            "college": "Example University", "degree": "B.Tech", "department": "Computer Science",
            "graduation_year": 2027, "cgpa": 8.4, "technical_skills": "SQL, React",
            "programming_languages": ["Python", "Java"], "preferred_language": "Python",
            "target_companies": ["Acme"], "target_roles": "Backend Engineer, SDE",
            "daily_study_target": 30, "weekly_study_target": 180,
        })
        self.assertEqual(response.status_code, 200)
        saved = self.one.get("/api/learning/profile").json["profile"]
        self.assertEqual(saved["technical_skills"], ["SQL", "React"])
        self.assertEqual(saved["target_companies"], ["Acme"])
        self.assertEqual(self.two.get("/api/learning/profile").json["profile"]["college"], "")
        self.assertEqual(self.two.get("/api/learning/profile").json["profile"]["target_companies"], [])
        self.assertEqual(self.one.put("/api/learning/profile", json={"cgpa": 11}).status_code, 400)
        self.assertEqual(self.one.put("/api/learning/profile", json={"daily_study_target": 80, "weekly_study_target": 60}).status_code, 400)
        self.assertEqual(self.app.test_client().get("/api/learning/profile").status_code, 401)

    def test_first_time_plan_and_actual_weak_topic_recommendation(self):
        self.one.put("/api/learning/profile", json={"daily_study_target": 30, "weekly_study_target": 180})
        first_plan = self.one.get("/api/learning/plan")
        self.assertEqual(first_plan.status_code, 200)
        self.assertGreaterEqual(len(first_plan.json["plan"]["tasks"]), 1)
        self.assertTrue(all(task["status"] == "pending" for task in first_plan.json["plan"]["tasks"]))
        self.assertTrue(any(item["kind"] == "daily_plan" for item in self.one.get("/api/learning/notifications").json["notifications"]))
        self.practice()
        progress = self.one.get("/api/practice/progress").json
        self.assertIn("Percentages", [row["topic"] for row in progress["recommendations"]])
        # Tomorrow's plan carries forward an unfinished weak task and keeps the priority data-driven.
        from app.services.learning import get_or_create_plan
        from datetime import date, timedelta
        tomorrow = get_or_create_plan(1, date.today() + timedelta(days=1))
        db.session.commit()
        self.assertTrue(any(row["topic"] == "Percentages" for row in tomorrow["tasks"]))
        task_id = tomorrow["tasks"][0]["id"]
        self.assertEqual(self.two.post(f"/api/learning/plan/tasks/{task_id}/complete").status_code, 404)
        self.assertEqual(self.one.post(f"/api/learning/plan/tasks/{task_id}/complete").status_code, 200)
        self.assertEqual(self.one.post(f"/api/learning/plan/tasks/{task_id}/complete").json["task"]["status"], "completed")

    def test_missions_rewards_weekly_progress_goals_and_notifications(self):
        self.one.put("/api/learning/profile", json={"daily_study_target": 15, "weekly_study_target": 60})
        created = self.one.get("/api/learning/missions")
        self.assertEqual(created.status_code, 200)
        self.assertEqual(len(created.json["missions"]["daily"]), 6)
        weak_mission_id = next(item["id"] for item in created.json["missions"]["daily"] if item["requirements"].get("metric") == "topic_sessions")
        self.practice()
        self.assertEqual(RewardTransaction.query.filter_by(user_id=1, activity_type="mission", activity_id=weak_mission_id).count(), 1)
        first = self.one.get("/api/learning/missions").json["missions"]
        weak_mission = next(item for item in first["daily"] if item["requirements"].get("metric") == "topic_sessions")
        self.assertEqual(weak_mission["progress"], 1)
        self.assertTrue(weak_mission["completed"])
        accuracy_mission = next(item for item in first["daily"] if item["requirements"].get("metric") == "topic_accuracy")
        self.assertEqual(accuracy_mission["progress"], 0)
        self.assertFalse(accuracy_mission["completed"])
        reward = RewardTransaction.query.filter_by(user_id=1, activity_type="mission", activity_id=weak_mission["id"]).first()
        self.assertIsNotNone(reward)
        self.assertEqual((reward.xp_earned, reward.coins_earned), (12, 5))
        self.one.get("/api/learning/missions")
        self.assertEqual(RewardTransaction.query.filter_by(user_id=1, activity_type="mission", activity_id=weak_mission["id"]).count(), 1)
        self.assertEqual(self.two.get("/api/learning/missions").json["missions"]["daily"][0]["progress"], 0)
        goals = self.one.get("/api/learning/goals").json["goals"]
        self.assertGreaterEqual(goals["today"]["minutes"], 2)
        self.assertGreaterEqual(goals["week"]["completed_activities"], 1)
        self.assertEqual(len(goals["daily_history"]), 7)
        notifications = self.one.get("/api/learning/notifications").json
        self.assertGreaterEqual(notifications["unread_count"], 2)
        self.assertTrue(any(row["kind"] == "mission_complete" for row in notifications["notifications"]))
        self.assertEqual(self.two.get("/api/learning/notifications").json["notifications"], [])
        note_id = notifications["notifications"][0]["id"]
        self.assertEqual(self.two.post(f"/api/learning/notifications/{note_id}/read").status_code, 404)
        self.assertTrue(self.one.post(f"/api/learning/notifications/{note_id}/read").json["notification"]["read"])
        self.assertLess(self.one.get("/api/learning/notifications").json["unread_count"], notifications["unread_count"])

    def test_weekly_missions_aggregate_saved_completed_sessions(self):
        for _ in range(5):
            self.practice()
        missions = self.one.get("/api/learning/missions").json["missions"]
        session_mission = next(item for item in missions["weekly"] if item["requirements"].get("metric") == "sessions")
        self.assertEqual(session_mission["progress"], 5)
        self.assertTrue(session_mission["completed"])
        self.one.get("/api/learning/missions")
        self.assertEqual(RewardTransaction.query.filter_by(user_id=1, activity_type="mission", activity_id=session_mission["id"]).count(), 1)
        self.assertEqual(RewardTransaction.query.filter_by(user_id=2, activity_type="mission").count(), 0)

    def test_achievement_level_streak_and_goal_missed_notifications(self):
        self.one.put("/api/learning/profile", json={"daily_study_target": 60, "weekly_study_target": 420})
        from app.models import GamificationProfile
        from app.services.gamification import award_activity
        now = datetime.now(timezone.utc)
        activity_day = now.date()
        profile = GamificationProfile(user_id=1)
        db.session.add(profile)
        db.session.flush()
        profile.total_xp = 99
        profile.current_streak = 6
        from datetime import date, timedelta
        profile.last_activity_date = activity_day - timedelta(days=1)
        award_activity(1, "practice", 9101, 5, 5, now=now)
        db.session.commit()
        kinds = {row.kind for row in LearningNotification.query.filter_by(user_id=1).all()}
        self.assertIn("achievement", kinds)
        self.assertIn("streak", kinds)
        self.assertIn("level_up", kinds)
        from app.services.learning import get_or_create_plan
        get_or_create_plan(1, activity_day + timedelta(days=1))
        db.session.commit()
        self.assertTrue(any(row.kind == "goal_missed" for row in LearningNotification.query.filter_by(user_id=1).all()))


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from app import create_app
from app.extensions import db
from app.models import AssessmentAttemptQuestion, Question
from app.services.nemotron import NemotronUnavailable

class StudentJourneyTests(unittest.TestCase):
    def setUp(self):
        folder = Path(__file__).resolve().parents[1] / "instance"; folder.mkdir(exist_ok=True)
        self.path = folder / f"journey-{uuid4().hex}.sqlite3"
        self.config = {"TESTING": True, "SECRET_KEY": "journey-secret", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.path.as_posix()}"}
        self.app = create_app(self.config); self.ctx = self.app.app_context(); self.ctx.push()
        self.client = self.app.test_client()

    def tearDown(self):
        if self.ctx:
            db.session.remove(); db.engine.dispose(); self.ctx.pop()
        for suffix in ("", "-journal", "-wal", "-shm"):
            Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def test_complete_student_journey_with_ai_fallback_and_restart_persistence(self):
        # Register the student's basic profile, then confirm normal login behavior.
        registered = self.client.post("/api/auth/register", json={"name":"Casey Journey","email":"casey-journey@test.local","password":"strong-pass-123"})
        self.assertEqual(registered.status_code, 201)
        self.assertEqual(registered.json["user"]["name"], "Casey Journey")
        self.client.post("/api/auth/logout")
        self.assertEqual(self.client.post("/api/auth/login", json={"email":"casey-journey@test.local","password":"strong-pass-123"}).status_code, 200)

        # Complete the initial assessment and view objective results.
        attempt_id = self.client.post("/api/assessments").json["attempt_id"]
        members = AssessmentAttemptQuestion.query.filter_by(attempt_id=attempt_id).order_by(AssessmentAttemptQuestion.position).all()
        for member in members:
            question = db.session.get(Question, member.question_id)
            response = self.client.put(f"/api/assessments/{attempt_id}/answers", json={"question_id":question.id,"selected_option":question.correct_option})
            self.assertEqual(response.status_code, 200)
        assessment = self.client.post(f"/api/assessments/{attempt_id}/submit")
        self.assertEqual(assessment.status_code, 200)
        self.assertEqual(assessment.json["attempt"]["score_percent"], 100.0)
        self.assertEqual(self.client.get(f"/api/assessments/{attempt_id}/results").status_code, 200)

        # AI features must still work safely when Nemotron is unavailable.
        with patch("app.routes.ai.NemotronClient") as model:
            model.return_value.complete_json.side_effect = NemotronUnavailable("offline")
            analysis = self.client.post("/api/ai/analysis", json={"attempt_id":attempt_id})
        self.assertEqual(analysis.status_code, 201)
        self.assertEqual(analysis.json["analysis"]["source"], "fallback")
        with patch("app.routes.ai.NemotronClient") as model:
            model.return_value.complete.side_effect = NemotronUnavailable("offline")
            chat = self.client.post("/api/ai/chat", json={"message":"How should I prepare for a technical interview?"})
        self.assertEqual(chat.status_code, 201)
        self.assertEqual(chat.json["source"], "fallback")
        with patch("app.routes.ai.NemotronClient") as model:
            model.return_value.complete_json.side_effect = NemotronUnavailable("offline")
            ai_question = self.client.post("/api/ai/practice-questions", json={"subject":"Technical"})
        self.assertEqual(ai_question.status_code, 201)
        self.assertEqual(ai_question.json["question"]["source"], "question_bank")

        # Repeated strong practice changes deterministic difficulty from easy to hard.
        first_session = None
        for _ in range(3):
            session = self.client.post("/api/practice/sessions", json={"subject":"Technical"}).json["session"]
            if first_session is None:
                first_session = session
            answers = []
            for item in session["questions"]:
                question = db.session.get(Question, item["id"])
                answers.append({"question_id":question.id,"selected_option":question.correct_option})
            submitted = self.client.post(f"/api/practice/sessions/{session['id']}/submit", json={"answers":answers})
            self.assertEqual(submitted.status_code, 200)
            self.assertIsNotNone(submitted.json["reward"])
        hard_session = self.client.post("/api/practice/sessions", json={"subject":"Technical"}).json["session"]
        self.assertEqual(hard_session["target_difficulty"], "hard")

        # Complete student preferences and inspect real rewards, leaderboard, readiness, and report.
        self.assertEqual(self.client.put("/api/readiness/companies", json={"companies":["Example Systems"]}).status_code, 200)
        rewards = self.client.get("/api/gamification").json
        self.assertGreater(rewards["profile"]["total_xp"], 0)
        self.assertGreater(rewards["profile"]["total_coins"], 0)
        self.assertEqual(rewards["leaderboard"][0]["name"], "Casey Journey")
        readiness = self.client.get("/api/readiness").json
        self.assertIsNotNone(readiness["readiness"]["score"])
        self.assertEqual(readiness["target_companies"], ["Example Systems"])
        with patch("app.routes.readiness.NemotronClient") as model:
            model.return_value.complete_json.side_effect = NemotronUnavailable("offline")
            report = self.client.post("/api/readiness/report", json={})
        self.assertEqual(report.status_code, 201)
        self.assertEqual(report.json["report"]["source"], "fallback")
        self.assertEqual(self.client.get("/api/readiness/report").json["report"]["id"], report.json["report"]["id"])

        # Log out and in again, then recreate the app on the same SQLite file.
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={"email":"casey-journey@test.local","password":"strong-pass-123"}).status_code, 200)
        cookie = self.client.get_cookie("session")
        db.session.remove(); db.engine.dispose(); self.ctx.pop(); self.ctx = None
        restarted = create_app(self.config)
        resumed = restarted.test_client(); resumed.set_cookie("session", cookie.value)
        self.assertEqual(resumed.get("/api/auth/me").json["user"]["name"], "Casey Journey")
        self.assertEqual(len(resumed.get("/api/assessments/history").json["attempts"]), 1)
        self.assertEqual(len(resumed.get("/api/ai/analysis").json["analyses"]), 1)
        self.assertEqual(len(resumed.get("/api/ai/chat/sessions").json["sessions"]), 1)
        self.assertEqual(len(resumed.get("/api/ai/practice-questions").json["questions"]), 1)
        self.assertGreater(resumed.get("/api/practice/progress").json["total_attempts"], 0)
        self.assertGreater(resumed.get("/api/gamification").json["profile"]["total_xp"], 0)
        self.assertIsNotNone(resumed.get("/api/readiness/report").json["report"])
        with restarted.app_context():
            db.session.remove(); db.engine.dispose()

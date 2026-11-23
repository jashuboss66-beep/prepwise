import unittest
from pathlib import Path
from uuid import uuid4
from app import create_app
from app.extensions import db
from app.models import PracticeAttempt, Question

class AdaptivePracticeTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / "instance"
        root.mkdir(exist_ok=True)
        self.path = root / f"phase4-{uuid4().hex}.sqlite3"
        self.config = {"TESTING": True, "SECRET_KEY": "phase4", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.path.as_posix()}"}
        self.app = create_app(self.config)
        self.ctx = self.app.app_context(); self.ctx.push()
        self.one, self.two = self.app.test_client(), self.app.test_client()
        self.one.post("/api/auth/register", json={"name":"One","email":"one@test.local","password":"password123"})
        self.two.post("/api/auth/register", json={"name":"Two","email":"two@test.local","password":"password123"})

    def tearDown(self):
        db.session.remove(); db.engine.dispose(); self.ctx.pop()
        self.path.unlink(missing_ok=True)
        Path(f"{self.path}-journal").unlink(missing_ok=True)

    def answer_session(self, client, session, correct):
        payload=[]
        for question in session["questions"]:
            row = db.session.get(Question, question["id"])
            option = row.correct_option if correct else (row.correct_option + 1) % 4
            payload.append({"question_id": row.id, "selected_option": option})
        return client.post(f"/api/practice/sessions/{session['id']}/submit", json={"answers": payload})

    def test_progression_recommendations_repetition_persistence_and_isolation(self):
        self.assertEqual(self.one.get("/api/practice/progress").json["total_attempts"], 0)
        first = self.one.post("/api/practice/sessions", json={"subject":"Technical"})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json["session"]["target_difficulty"], "easy")
        first_session = first.json["session"]
        self.assertEqual(len({q["id"] for q in first_session["questions"]}), len(first_session["questions"]))
        result = self.answer_session(self.one, first_session, True)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["result"]["accuracy"], 100.0)
        self.assertEqual(PracticeAttempt.query.filter_by(user_id=1).count(), len(first_session["questions"]))
        second = self.one.post("/api/practice/sessions", json={"subject":"Technical"}).json["session"]
        self.assertEqual(second["target_difficulty"], "hard")
        self.assertFalse(set(q["id"] for q in first_session["questions"]) & set(q["id"] for q in second["questions"]))

        weak = self.one.post("/api/practice/sessions", json={"subject":"Aptitude", "topic":"Percentages"}).json["session"]
        self.answer_session(self.one, weak, False)
        progress = self.one.get("/api/practice/progress").json
        self.assertTrue(any(item["topic"] == "Percentages" and item["accuracy"] == 0 for item in progress["topics"]))
        self.assertIn("Percentages", [item["topic"] for item in progress["recommendations"]])
        self.assertTrue(progress["accuracy_trend"])
        self.assertEqual(self.two.get("/api/practice/progress").json["total_attempts"], 0)
        self.assertGreaterEqual(db.session.query(PracticeAttempt).filter_by(user_id=1).count(), 7)

        # Practice data remains available after a fresh app instance opens the same SQLite file.
        db.session.remove()
        persisted = self.one.get("/api/practice/progress")
        self.assertEqual(persisted.status_code, 200)
        self.assertGreaterEqual(persisted.json["total_attempts"], 7)

    def test_session_ownership_and_answer_validation(self):
        session = self.one.post("/api/practice/sessions", json={"subject":"Verbal Ability"}).json["session"]
        self.assertEqual(self.two.post(f"/api/practice/sessions/{session['id']}/submit", json={"answers":[]}).status_code, 404)
        bad = self.one.post(f"/api/practice/sessions/{session['id']}/submit", json={"answers":[{"question_id":session['questions'][0]['id'],"selected_option":7}]})
        self.assertEqual(bad.status_code, 400)

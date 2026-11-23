import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from app import create_app
from app.extensions import db
from app.models import PlacementReport, Question

class ReadinessAnalyticsTests(unittest.TestCase):
    def setUp(self):
        folder = Path(__file__).resolve().parents[1] / "instance"; folder.mkdir(exist_ok=True)
        self.path = folder / f"phase6-{uuid4().hex}.sqlite3"
        self.config = {"TESTING": True, "SECRET_KEY": "phase6", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.path.as_posix()}"}
        self.app = create_app(self.config); self.ctx = self.app.app_context(); self.ctx.push()
        self.client, self.other = self.app.test_client(), self.app.test_client()
        self.client.post("/api/auth/register", json={"name":"Riley Analyst","email":"riley@test.local","password":"password123"})
        self.other.post("/api/auth/register", json={"name":"Jordan Analyst","email":"jordan@test.local","password":"password123"})

    def tearDown(self):
        db.session.remove(); db.engine.dispose(); self.ctx.pop()
        for suffix in ("", "-journal", "-wal", "-shm"):
            Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def test_empty_history_marks_categories_pending_without_zero_score(self):
        response = self.client.get("/api/readiness")
        self.assertEqual(response.status_code, 200)
        payload = response.json
        self.assertIsNone(payload["readiness"]["score"])
        self.assertEqual(payload["readiness"]["status"], "pending")
        self.assertTrue(all(item["score"] is None and item["status"] == "pending" for item in payload["readiness"]["components"]))
        self.assertEqual(payload["analytics"]["accuracy_trend"], [])
        self.assertEqual(payload["analytics"]["difficulty_distribution"], {"easy":0,"medium":0,"hard":0})
        self.assertEqual(self.other.get("/api/readiness").json["readiness"]["score"], None)

    def test_readiness_normalizes_available_weights_and_analytics_use_saved_answers(self):
        started = self.client.post("/api/assessments").json["attempt_id"]
        questions = self.client.get(f"/api/assessments/{started}").json["questions"]
        for index, item in enumerate(questions[:10]):
            key = db.session.get(Question, item["id"]).correct_option
            selected = key if index < 5 else (key + 1) % 4
            self.assertEqual(self.client.put(f"/api/assessments/{started}/answers", json={"question_id":item["id"],"selected_option":selected}).status_code, 200)
        self.assertEqual(self.client.post(f"/api/assessments/{started}/submit").status_code, 200)
        response = self.client.get("/api/readiness")
        self.assertEqual(response.status_code, 200)
        payload = response.json
        components = {item["key"]: item for item in payload["readiness"]["components"]}
        self.assertEqual(components["A"]["score"], 100.0)
        self.assertEqual(components["T"]["status"], "pending")
        self.assertEqual(components["C"]["status"], "pending")
        self.assertEqual(components["M"]["score"], 50.0)
        self.assertEqual(components["S"]["score"], 5.0)
        # (0.25*100 + 0.15*50 + 0.10*5) / (0.25+0.15+0.10) = 66
        self.assertEqual(payload["readiness"]["score"], 66.0)
        self.assertEqual(payload["readiness"]["status"], "partial")
        self.assertEqual(payload["analytics"]["accuracy_trend"][-1]["score"], 50.0)
        self.assertEqual(payload["analytics"]["subject_performance"][0]["accuracy"], 100.0)
        self.assertGreater(payload["profile"]["answered_questions"], 0)
        practice = self.client.post("/api/practice/sessions", json={"subject":"Technical"}).json["session"]
        answers = []
        for index, item in enumerate(practice["questions"]):
            question = db.session.get(Question, item["id"])
            selected = question.correct_option if index < 4 else (question.correct_option + 1) % 4
            answers.append({"question_id":question.id,"selected_option":selected})
        self.assertEqual(self.client.post(f"/api/practice/sessions/{practice['id']}/submit", json={"answers":answers}).status_code, 200)
        updated = self.client.get("/api/readiness").json
        self.assertEqual(updated["analytics"]["subject_performance"][-1]["accuracy"], 80.0)
        self.assertTrue(updated["analytics"]["mastery_radar"])
        self.assertTrue(any(item["answered"] > 0 for item in updated["analytics"]["practice_activity"]))
        self.assertEqual(sum(updated["analytics"]["difficulty_distribution"].values()), 5)
        # Different students cannot view each other's report or practice data.
        self.assertEqual(self.other.get("/api/readiness").json["profile"]["answered_questions"], 0)

    def test_company_preferences_report_validation_and_sqlite_persistence(self):
        saved = self.client.put("/api/readiness/companies", json={"companies":["Northstar Labs", "Example Systems", "northstar labs"]})
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json["companies"], ["Northstar Labs", "Example Systems"])
        self.assertEqual(self.other.get("/api/readiness").json["target_companies"], [])
        payload = {"summary":"Your preparation records are ready for a focused plan.",
                   "assessment_analysis":"No assessment results are recorded yet, so the assessment portion remains pending.",
                   "skill_analysis":[{"label":"Baseline","guidance":"Complete a first assessment to establish an initial measured baseline."}],
                   "recommendations":["Complete an assessment and review the saved results."],
                   "company_preparation":[{"company":"Northstar Labs","guidance":"Review the role description and practice relevant fundamentals."},
                                          {"company":"Example Systems","guidance":"Prepare project explanations and consult official role information."}]}
        with patch("app.routes.readiness.NemotronClient") as client:
            client.return_value.complete_json.return_value = payload
            response = self.client.post("/api/readiness/report", json={})
            prompt_context = client.return_value.complete_json.call_args.args[0][1]["content"]
            self.assertNotIn("Riley Analyst", prompt_context)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["report"]["source"], "nemotron")
        self.assertEqual(len(response.json["report"]["narrative"]["company_preparation"]), 2)
        self.assertEqual(self.other.get("/api/readiness/report").json["report"], None)
        report_id = response.json["report"]["id"]
        db.session.remove()
        self.assertEqual(PlacementReport.query.filter_by(id=report_id, user_id=1).count(), 1)

    def test_invalid_ai_report_falls_back_to_data_based_report(self):
        with patch("app.routes.readiness.NemotronClient") as client:
            client.return_value.complete_json.return_value = {"summary":"bad"}
            response = self.client.post("/api/readiness/report", json={})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["report"]["source"], "fallback")
        self.assertIn("establish a baseline", response.json["report"]["narrative"]["recommendations"][0])

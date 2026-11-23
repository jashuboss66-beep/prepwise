import unittest
from unittest.mock import patch
from pathlib import Path
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.models import (AssessmentAnswer, AssessmentAttempt, AssessmentAttemptQuestion, PracticeSession,
                        PracticeSessionQuestion, Question, QuestionBookmark, RewardTransaction)


class PlacementHubTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / "instance"; root.mkdir(exist_ok=True)
        self.path = root / f"hub-{uuid4().hex}.sqlite3"
        self.app = create_app({"TESTING": True, "SECRET_KEY": "hub", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.path.as_posix()}"})
        self.ctx = self.app.app_context(); self.ctx.push()
        self.a, self.b = self.app.test_client(), self.app.test_client()
        self.a.post("/api/auth/register", json={"name": "A Student", "email": f"a-{uuid4().hex}@hub.local", "password": "password123"})
        self.b.post("/api/auth/register", json={"name": "B Student", "email": f"b-{uuid4().hex}@hub.local", "password": "password123"})

    def tearDown(self):
        db.session.remove(); db.engine.dispose(); self.ctx.pop()
        for suffix in ("", "-journal", "-wal", "-shm"): Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def test_seeded_bank_targets_and_metadata(self):
        for category, count in (("Aptitude", 200), ("Communication", 150), ("Technical", 250)):
            rows = Question.query.filter_by(category=category).all()
            self.assertEqual(len(rows), count)
            self.assertTrue(all(len(row.options) == 4 and row.correct_option in range(4) and row.explanation for row in rows))
            self.assertTrue(all(row.source and row.license and row.topic and row.difficulty in ("easy", "medium", "hard") for row in rows))
        prompts = [row.prompt for row in Question.query.filter(Question.category.in_(["Aptitude", "Communication", "Technical"])).all()]
        self.assertEqual(len(prompts), len(set(prompts)))

    def test_normal_practice_bookmark_answers_rewards_and_isolation(self):
        started = self.a.post("/api/hub/normal/sessions", json={"category": "Aptitude", "count": 2})
        self.assertEqual(started.status_code, 201)
        session_id = started.json["session"]["id"]
        q = started.json["session"]["questions"][0]
        self.assertEqual(self.a.put(f"/api/hub/bookmarks/{q['id']}", json={"bookmarked": True}).status_code, 200)
        self.assertEqual(len(self.a.get("/api/hub/bookmarks").json["questions"]), 1)
        self.assertEqual(self.b.get("/api/hub/bookmarks").json["questions"], [])
        correct = db.session.get(Question, q["id"]).correct_option
        result = self.a.post(f"/api/hub/normal/sessions/{session_id}/answer", json={"question_id": q["id"], "selected_option": correct})
        self.assertTrue(result.json["answer"]["is_correct"])
        self.assertEqual(self.b.post(f"/api/hub/normal/sessions/{session_id}/answer", json={"question_id": q["id"], "selected_option": correct}).status_code, 404)
        self.assertEqual(self.a.post(f"/api/hub/normal/sessions/{session_id}/complete").status_code, 200)
        self.a.post(f"/api/hub/normal/sessions/{session_id}/complete")
        self.assertEqual(RewardTransaction.query.filter_by(user_id=1, activity_type="practice", activity_id=session_id).count(), 1)

    def test_ai_assessments_are_unique_randomized_timed_and_metrics_use_saved_data(self):
        first = self.a.post("/api/hub/assessments", json={"category":"Aptitude","difficulty":"mixed","question_count":6,"duration_minutes":10})
        second = self.a.post("/api/hub/assessments", json={"category":"Aptitude","difficulty":"mixed","question_count":6,"duration_minutes":10})
        self.assertEqual(first.status_code, 201); self.assertEqual(second.status_code, 201)
        one = db.session.get(AssessmentAttempt, first.json["attempt_id"]); two = db.session.get(AssessmentAttempt, second.json["attempt_id"])
        q1 = AssessmentAttemptQuestion.query.filter_by(attempt_id=one.id).all(); q2 = AssessmentAttemptQuestion.query.filter_by(attempt_id=two.id).all()
        self.assertEqual(len({x.question_id for x in q1}), 6); self.assertEqual(len({x.question_id for x in q2}), 6)
        self.assertNotEqual({x.question_id for x in q1}, {x.question_id for x in q2})
        self.assertTrue(all(sorted(x.option_order) == [0,1,2,3] for x in q1))
        data = self.a.get(f"/api/assessments/{one.id}").json
        for i, question in enumerate(data["questions"]):
            self.a.post(f"/api/assessments/{one.id}/questions/{question['id']}/view")
            self.a.put(f"/api/assessments/{one.id}/answers", json={"question_id":question["id"],"selected_option":0 if i%2==0 else None})
        self.a.post(f"/api/assessments/{one.id}/submit")
        with patch("app.routes.ai.NemotronClient.complete_json", return_value={}):
            analysis = self.a.post("/api/ai/analysis", json={"attempt_id":one.id})
        self.assertEqual(analysis.status_code, 201)
        # Force the local fallback, which is also required to attach verified metrics.
        self.assertIn("metrics", analysis.json["analysis"]["content"])
        self.assertEqual(analysis.json["analysis"]["content"]["metrics"]["overall"]["total"], 6)
        self.assertEqual(len(analysis.json["analysis"]["content"]["seven_day_roadmap"]), 7)
        self.assertEqual(self.b.get(f"/api/assessments/{one.id}/results").status_code, 404)
        timed = self.a.post("/api/hub/assessments", json={"category":"Technical","difficulty":"mixed","question_count":5,"duration_minutes":1})
        timed_attempt = db.session.get(AssessmentAttempt, timed.json["attempt_id"])
        timed_attempt.started_at = datetime.now(timezone.utc) - timedelta(minutes=2); db.session.commit()
        timed_question = AssessmentAttemptQuestion.query.filter_by(attempt_id=timed_attempt.id).first()
        self.assertEqual(self.a.put(f"/api/assessments/{timed_attempt.id}/answers", json={"question_id":timed_question.question_id,"selected_option":0}).status_code, 409)
        self.assertEqual(self.a.post(f"/api/assessments/{timed_attempt.id}/submit").status_code, 200)

    def test_daily_quiz_answers_survive_reload_and_payout_is_single(self):
        first = self.a.get("/api/hub/daily-quiz"); self.assertEqual(first.status_code, 200)
        quiz = first.json["quiz"]
        self.assertEqual(len(quiz["questions"]), 10)
        self.assertCountEqual([q["category"] for q in quiz["questions"]], ["Aptitude"]*4+["Communication"]*3+["Technical"]*3)
        for q in quiz["questions"][:6]:
            self.a.post(f"/api/hub/daily-quiz/{quiz['session_id']}/answer", json={"question_id":q["id"],"selected_option":0})
        reloaded = self.a.get("/api/hub/daily-quiz").json["quiz"]
        self.assertEqual(reloaded["answered"], 6)
        submitted = self.a.post(f"/api/hub/daily-quiz/{quiz['session_id']}/submit").json["result"]
        self.assertTrue(submitted["completed"]); self.assertEqual(submitted["answered"], 6)
        self.a.post(f"/api/hub/daily-quiz/{quiz['session_id']}/submit")
        self.assertEqual(RewardTransaction.query.filter_by(user_id=1, activity_type="practice", activity_id=quiz["session_id"]).count(), 1)
        other = self.b.get("/api/hub/daily-quiz").json["quiz"]
        self.assertNotEqual(other["session_id"], quiz["session_id"])


if __name__ == "__main__": unittest.main()

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.models import AssessmentAnswer, AssessmentAttempt, AssessmentSubjectResult, Question


class AssessmentWorkflowTests(unittest.TestCase):
    def setUp(self):
        instance_dir = Path(__file__).resolve().parents[1] / "instance"
        instance_dir.mkdir(exist_ok=True)
        self.database_path = instance_dir / f"phase2-tests-{uuid4().hex}.sqlite3"
        database_url = f"sqlite:///{self.database_path.as_posix()}"
        self.test_config = {
            "TESTING": True,
            "SECRET_KEY": "assessment-test-secret",
            "SQLALCHEMY_DATABASE_URI": database_url,
        }
        self.app = create_app(self.test_config)
        self.context = self.app.app_context()
        self.context.push()
        self.student = self.app.test_client()
        self.other_student = self.app.test_client()
        self.assertEqual(self.student.post("/api/assessments").status_code, 401)
        self.student.post("/api/auth/register", json={
            "name": "Taylor Student",
            "email": "taylor@example.test",
            "password": "password123",
        })
        self.other_student.post("/api/auth/register", json={
            "name": "Morgan Student",
            "email": "morgan@example.test",
            "password": "password123",
        })

    def tearDown(self):
        if self.context:
            db.session.remove()
            db.engine.dispose()
            self.context.pop()
        for path in (self.database_path, Path(f"{self.database_path}-journal"), Path(f"{self.database_path}-wal"), Path(f"{self.database_path}-shm")):
            path.unlink(missing_ok=True)

    def test_scoring_review_history_isolation_and_sqlite_persistence(self):
        attempt_id = self.student.post("/api/assessments").json["attempt_id"]
        assessment = self.student.get(f"/api/assessments/{attempt_id}")
        self.assertEqual(assessment.status_code, 200)
        questions = assessment.json["questions"]
        self.assertEqual(len(questions), 20)
        self.assertNotIn("correct_option", questions[0])

        subject_question_count = {}
        for question in questions:
            subject_question_count[question["subject"]] = subject_question_count.get(question["subject"], 0) + 1
            correct = db.session.get(Question, question["id"]).correct_option
            if question["subject"] == "Technical":
                selected = correct
            elif question["subject"] == "Aptitude":
                selected = (correct + 1) % 4
            else:
                selected = correct if subject_question_count[question["subject"]] <= 3 else (correct + 1) % 4
            response = self.student.put(
                f"/api/assessments/{attempt_id}/answers",
                json={"question_id": question["id"], "selected_option": selected},
            )
            self.assertEqual(response.status_code, 200)

        self.assertEqual(set(subject_question_count.values()), {5})
        result = self.student.post(f"/api/assessments/{attempt_id}/submit")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["attempt"]["correct_answers"], 11)
        self.assertEqual(result.json["attempt"]["score_percent"], 55.0)
        insights = {item["subject"]: item["insight"] for item in result.json["subjects"]}
        self.assertEqual(insights["Technical"], "Strength")
        self.assertEqual(insights["Aptitude"], "Needs focus")
        self.assertEqual(insights["Logical Reasoning"], "Developing")
        self.assertEqual(len(result.json["questions"]), 20)
        self.assertEqual(self.student.get(f"/api/assessments/{attempt_id}/results").status_code, 200)
        self.assertEqual(self.student.post(f"/api/assessments/{attempt_id}/submit").json["attempt"]["correct_answers"], 11)
        self.assertEqual(self.student.put(
            f"/api/assessments/{attempt_id}/answers",
            json={"question_id": questions[0]["id"], "selected_option": 0},
        ).status_code, 409)

        self.assertEqual(len(self.student.get("/api/assessments/history").json["attempts"]), 1)
        self.assertEqual(self.other_student.get("/api/assessments/history").json["attempts"], [])
        self.assertEqual(self.other_student.get(f"/api/assessments/{attempt_id}").status_code, 404)
        self.assertEqual(self.other_student.put(
            f"/api/assessments/{attempt_id}/answers",
            json={"question_id": questions[0]["id"], "selected_option": 0},
        ).status_code, 404)
        self.assertEqual(self.other_student.get(f"/api/assessments/{attempt_id}/results").status_code, 404)
        self.assertEqual(self.other_student.post(f"/api/assessments/{attempt_id}/submit").status_code, 404)
        other_attempt_id = self.other_student.post("/api/assessments").json["attempt_id"]
        self.assertEqual(self.other_student.get("/api/assessments/history").json["attempts"][0]["id"], other_attempt_id)
        self.assertEqual([item["id"] for item in self.student.get("/api/assessments/history").json["attempts"]], [attempt_id])
        self.assertEqual(AssessmentAttempt.query.count(), 2)
        self.assertEqual(AssessmentAnswer.query.filter_by(attempt_id=attempt_id).count(), 20)
        self.assertEqual(AssessmentSubjectResult.query.filter_by(attempt_id=attempt_id).count(), 4)

        cookie = self.student.get_cookie("session")
        db.session.remove()
        db.engine.dispose()
        self.context.pop()
        self.context = None
        restarted_app = create_app(self.test_config)
        restarted_client = restarted_app.test_client()
        restarted_client.set_cookie("session", cookie.value)
        self.assertEqual([item["id"] for item in restarted_client.get("/api/assessments/history").json["attempts"]], [attempt_id])
        with restarted_app.app_context():
            self.assertEqual(AssessmentAttempt.query.count(), 2)
            self.assertEqual(Question.query.filter_by(practice_only=False).count(), 20)
            db.session.remove()
            db.engine.dispose()

    def test_expired_attempt_rejects_new_answers_and_can_be_submitted(self):
        attempt_id = self.student.post("/api/assessments").json["attempt_id"]
        attempt = db.session.get(AssessmentAttempt, attempt_id)
        attempt.started_at = datetime.now(timezone.utc) - timedelta(minutes=21)
        db.session.commit()
        question_id = self.student.get(f"/api/assessments/{attempt_id}").json["questions"][0]["id"]
        response = self.student.put(
            f"/api/assessments/{attempt_id}/answers",
            json={"question_id": question_id, "selected_option": 0},
        )
        self.assertEqual(response.status_code, 409)
        result = self.student.post(f"/api/assessments/{attempt_id}/submit")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["attempt"]["correct_answers"], 0)


if __name__ == "__main__":
    unittest.main()

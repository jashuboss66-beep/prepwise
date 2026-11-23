import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.models import (
    AIAnalysis,
    AIChatMessage,
    AIChatSession,
    AIPracticeQuestion,
    AssessmentAttempt,
    AssessmentSubjectResult,
    User,
)
from app.services.ai_features import validate_practice_question
from app.services.nemotron import (
    NEMOTRON_MODEL,
    OPENROUTER_URL,
    NemotronClient,
    NemotronUnavailable,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class AIFeatureTests(unittest.TestCase):
    def setUp(self):
        instance_dir = Path(__file__).resolve().parents[1] / "instance"
        instance_dir.mkdir(exist_ok=True)
        self.database_path = instance_dir / f"phase3-tests-{uuid4().hex}.sqlite3"
        self.config = {
            "TESTING": True,
            "SECRET_KEY": "phase3-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path.as_posix()}",
        }
        self.app = create_app(self.config)
        self.context = self.app.app_context()
        self.context.push()
        self.student = self.app.test_client()
        self.other_student = self.app.test_client()
        self.student.post("/api/auth/register", json={"name": "Private Student", "email": "private@example.test", "password": "password123"})
        self.other_student.post("/api/auth/register", json={"name": "Other Student", "email": "other@example.test", "password": "password123"})
        self.user = User.query.filter_by(email="private@example.test").first()
        self.other_user = User.query.filter_by(email="other@example.test").first()
        self.attempt = AssessmentAttempt(
            user_id=self.user.id,
            duration_seconds=1200,
            completed_at=datetime.now(timezone.utc),
            correct_answers=11,
            total_questions=20,
            score_percent=55.0,
        )
        self.other_attempt = AssessmentAttempt(
            user_id=self.other_user.id,
            duration_seconds=1200,
            completed_at=datetime.now(timezone.utc),
            correct_answers=5,
            total_questions=20,
            score_percent=25.0,
        )
        db.session.add_all([self.attempt, self.other_attempt])
        db.session.flush()
        self.scores = [
            ("Aptitude", 1, 5, 20.0, "Needs focus"),
            ("Logical Reasoning", 3, 5, 60.0, "Developing"),
            ("Verbal Ability", 2, 5, 40.0, "Needs focus"),
            ("Technical", 5, 5, 100.0, "Strength"),
        ]
        other_scores = [(subject, 1, 5, 20.0, "Needs focus") for subject, *_ in self.scores]
        for attempt, score_rows in ((self.attempt, self.scores), (self.other_attempt, other_scores)):
            db.session.add_all(AssessmentSubjectResult(
                attempt_id=attempt.id,
                subject=subject,
                correct_answers=correct,
                total_questions=total,
                score_percent=percentage,
                insight=insight,
            ) for subject, correct, total, percentage, insight in score_rows)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()
        for path in (self.database_path, Path(f"{self.database_path}-journal"), Path(f"{self.database_path}-wal"), Path(f"{self.database_path}-shm")):
            path.unlink(missing_ok=True)

    @staticmethod
    def valid_analysis_payload():
        return {
            "summary": "Your recorded results show a clear starting point for focused preparation.",
            "subject_advice": [
                {"subject": subject, "guidance": f"Use a deliberate review routine for {subject}.", "activities": ["Review one worked example.", "Complete a short question set."]}
                for subject in ("Aptitude", "Logical Reasoning", "Verbal Ability", "Technical")
            ],
            "roadmap": [
                {"week": week, "focus": f"Build week {week} study habits", "activities": ["Practice a short set.", "Review mistakes and explanations."]}
                for week in range(1, 5)
            ],
        }

    def test_openrouter_client_uses_backend_key_free_model_and_supported_endpoint(self):
        captured = {}

        def fake_opener(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = request.headers
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse({"choices": [{"message": {"content": "{\"ok\": true}"}}]})

        client = NemotronClient(api_key_provider=lambda: "test-backend-key", opener=fake_opener)
        self.assertEqual(client.complete_json([{"role": "user", "content": "Return JSON."}]), {"ok": True})
        self.assertEqual(captured["url"], OPENROUTER_URL)
        self.assertEqual(captured["payload"]["model"], NEMOTRON_MODEL)
        self.assertEqual(captured["headers"]["Authorization"], "Bearer test-backend-key")
        self.assertEqual(captured["timeout"], 35)
        self.assertNotIn("test-backend-key", json.dumps(captured["payload"]))

        missing_key = NemotronClient(api_key_provider=lambda: "", opener=lambda *_args, **_kwargs: self.fail("must not call OpenRouter"))
        with self.assertRaises(NemotronUnavailable):
            missing_key.complete([{"role": "user", "content": "Hello."}])

    def test_analysis_chat_and_practice_use_validated_nemotron_outputs(self):
        with patch("app.routes.ai.NemotronClient.complete_json", side_effect=[self.valid_analysis_payload(), {
            "subject": "Aptitude",
            "prompt": "A value increases from 80 to 100. What is the percentage increase?",
            "options": ["20%", "25%", "30%", "40%"],
            "correct_option": 1,
            "explanation": "The increase is 20; divide by the original 80 to get 25%.",
        }]), patch("app.routes.ai.NemotronClient.complete", return_value="Start by writing the original value and the change before calculating a percentage.") as chat_call:
            analysis_response = self.student.post("/api/ai/analysis", json={"attempt_id": self.attempt.id})
            self.assertEqual(analysis_response.status_code, 201)
            analysis = analysis_response.json["analysis"]
            self.assertEqual(analysis["source"], "nemotron")
            self.assertEqual(analysis["content"]["actual_scores"][0]["score_percent"], 20.0)
            self.assertEqual(analysis["content"]["strengths"][0]["subject"], "Technical")
            self.assertEqual(analysis["content"]["weaknesses"][0]["subject"], "Aptitude")
            self.assertEqual(analysis["content"]["priorities"][0]["subject"], "Aptitude")
            self.assertEqual(len(analysis["content"]["roadmap"]), 4)

            practice_response = self.student.post("/api/ai/practice-questions", json={"subject": "Aptitude", "attempt_id": self.attempt.id})
            self.assertEqual(practice_response.status_code, 201)
            self.assertEqual(practice_response.json["question"]["source"], "nemotron")
            self.assertEqual(len(practice_response.json["question"]["options"]), 4)
            self.assertEqual(practice_response.json["question"]["correct_option"], 1)

            chat_response = self.student.post("/api/ai/chat", json={"message": "How should I practice percentages?"})
            self.assertEqual(chat_response.status_code, 201)
            self.assertEqual(chat_response.json["source"], "nemotron")
            sent_messages = chat_call.call_args.args[0]
            sent_prompt = json.dumps(sent_messages)
            self.assertIn("Needs focus", sent_prompt)
            self.assertNotIn("20.0", sent_prompt)
            self.assertNotIn(self.user.name, sent_prompt)
            self.assertNotIn(self.user.email, sent_prompt)
            self.assertNotIn('"attempt_id"', sent_prompt)

        self.assertEqual(len(self.student.get("/api/ai/analysis").json["analyses"]), 1)
        self.assertEqual(self.student.get("/api/ai/practice-questions").json["questions"][0]["source"], "nemotron")
        chat_session = chat_response.json["session_id"]
        self.assertEqual(len(self.student.get(f"/api/ai/chat/sessions/{chat_session}").json["messages"]), 2)
        self.assertEqual(self.other_student.get(f"/api/ai/chat/sessions/{chat_session}").status_code, 404)
        self.assertEqual(self.other_student.post("/api/ai/analysis", json={"attempt_id": self.attempt.id}).status_code, 404)
        self.assertEqual(self.student.get("/api/ai/chat/sessions").json["sessions"][0]["id"], chat_session)

    def test_invalid_or_unavailable_model_responses_use_stored_local_fallbacks(self):
        malformed_question = {
            "subject": "Verbal Ability",
            "prompt": "Choose the correct word for the sentence.",
            "options": ["same", "same", "other", "another"],
            "correct_option": 0,
            "explanation": "The duplicated options make this invalid.",
        }
        invalid_analysis = {"summary": "bad", "subject_advice": [], "roadmap": []}
        with patch("app.routes.ai.NemotronClient.complete_json", side_effect=[invalid_analysis, malformed_question]), patch("app.routes.ai.NemotronClient.complete", side_effect=NemotronUnavailable("offline")) as chat_call:
            analysis = self.student.post("/api/ai/analysis", json={"attempt_id": self.attempt.id})
            self.assertEqual(analysis.status_code, 201)
            self.assertEqual(analysis.json["analysis"]["source"], "fallback")
            self.assertEqual(analysis.json["analysis"]["content"]["actual_scores"][0]["score_percent"], 20.0)
            self.assertIn("55.0%", analysis.json["analysis"]["content"]["summary"])

            practice = self.student.post("/api/ai/practice-questions", json={"subject": "Verbal Ability"})
            self.assertEqual(practice.status_code, 201)
            self.assertEqual(practice.json["question"]["source"], "question_bank")
            self.assertEqual(len(practice.json["question"]["options"]), 4)

            reply = self.student.post("/api/ai/chat", json={"message": "Give me a Python DSA practice tip. Contact me at private@example.test or +1 415 555 0199"})
            self.assertEqual(reply.status_code, 201)
            self.assertEqual(reply.json["source"], "fallback")
            captured_text = json.dumps(chat_call.call_args_list[0].args[0])
            self.assertNotIn("private@example.test", captured_text)
            self.assertNotIn("415 555 0199", captured_text)
            personalized = self.student.post("/api/ai/chat", json={"session_id": reply.json["session_id"], "message": "How should I practice aptitude percentages?"})
            self.assertEqual(personalized.status_code, 201)
            self.assertIn("20.0%", personalized.json["assistant_message"]["content"])

        self.assertEqual(AIAnalysis.query.filter_by(user_id=self.user.id).count(), 1)
        self.assertEqual(AIPracticeQuestion.query.filter_by(user_id=self.user.id).count(), 1)
        self.assertEqual(AIChatSession.query.filter_by(user_id=self.user.id).count(), 1)
        self.assertEqual(AIChatMessage.query.filter_by(user_id=self.user.id).count(), 4)
        self.assertEqual(self.other_student.get("/api/ai/analysis").json["analyses"], [])

    def test_response_validation_rejects_malformed_questions_and_bad_requests(self):
        invalid = {
            "subject": "Aptitude",
            "prompt": "Choose the correct value for this question.",
            "options": ["Same", "Same", "Other", "Another"],
            "correct_option": 0,
            "explanation": "The first option is the answer.",
        }
        with self.assertRaises(ValueError):
            validate_practice_question(invalid, "Aptitude")
        self.assertEqual(self.student.post("/api/ai/practice-questions", json={"subject": "Writing"}).status_code, 400)
        self.assertEqual(self.student.post("/api/ai/chat", json={"message": "  "}).status_code, 400)
        self.assertEqual(self.student.post("/api/ai/chat", json=[]).status_code, 400)
        self.assertEqual(self.student.post("/api/ai/analysis", json=[]).status_code, 400)
        self.assertEqual(self.other_student.get("/api/ai/practice-questions").json["questions"], [])


if __name__ == "__main__":
    unittest.main()

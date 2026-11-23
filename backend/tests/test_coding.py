import unittest
from pathlib import Path
from io import BytesIO
from uuid import uuid4
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from app import create_app
from app.extensions import db
from app.models import CodingSubmission, RewardTransaction
from app.services.readiness import build_readiness

class CodingPracticeTests(unittest.TestCase):
    def setUp(self):
        folder = Path(__file__).resolve().parents[1] / "instance"; folder.mkdir(exist_ok=True)
        self.path = folder / f"coding-{uuid4().hex}.sqlite3"
        self.app = create_app({"TESTING": True, "SECRET_KEY": "coding", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.path.as_posix()}"})
        self.context = self.app.app_context(); self.context.push()
        self.one, self.two = self.app.test_client(), self.app.test_client()
        self.one.post("/api/auth/register", json={"name": "One", "email": f"one-{uuid4().hex}@test.local", "password": "password123"})
        self.two.post("/api/auth/register", json={"name": "Two", "email": f"two-{uuid4().hex}@test.local", "password": "password123"})
    def tearDown(self):
        db.session.remove(); db.engine.dispose(); self.context.pop()
        for suffix in ("", "-journal", "-wal", "-shm"): Path(f"{self.path}{suffix}").unlink(missing_ok=True)
    def test_problem_catalog_auth_and_language_templates(self):
        self.assertEqual(self.app.test_client().get("/api/coding/problems").status_code, 401)
        res = self.one.get("/api/coding/problems"); self.assertEqual(len(res.json["problems"]), 3)
        self.assertEqual({x["id"] for x in res.json["languages"]}, {"python", "cpp", "java", "javascript"})
        self.assertIn("#include", self.one.get("/api/coding/problems?language=cpp").json["problems"][0]["starter_code"])
        self.assertEqual(self.one.get("/api/coding/problems?language=ruby").status_code, 400)
        self.assertEqual(self.two.get("/api/coding/history").json["submissions"], [])
    @patch("app.routes.coding._wandbox_request")
    @patch("app.routes.coding._compilers", return_value=[{"name":"gcc-head","language":"C++","switches":[]},{"name":"gcc-stable","language":"C++","switches":[{"name":"gnu++17","default":True}]}])
    def test_runner_resolves_catalog_and_compiles_each_case(self, _catalog, run):
        run.side_effect = [{"status":"0","program_output":"2\n","time":"0.01"},{"status":"0","program_output":"4\n","time":"0.02"}]
        from app.routes.coding import _run_cases
        self.assertEqual(_run_cases("int main(){}", [("a","2"),("b","4")], "cpp"), (2,.02,None))
        self.assertEqual(run.call_count, 2)
        payload = run.call_args_list[0].args[1]
        self.assertEqual((payload["compiler"], payload["options"]), ("gcc-stable","gnu++17"))
        self.assertEqual(payload["stdin"], "a")
        self.assertEqual(run.call_args_list[1].args[1]["stdin"], "b")
    @patch("app.routes.coding._run_cases", side_effect=HTTPError("https://wandbox.org/api/compile.json", 403, "Forbidden", {}, BytesIO(b"blocked by network policy")))
    def test_runner_403_explains_service_denial(self, _run):
        response = self.one.post("/api/coding/submit", json={"problem_id": "pair-target-indices", "source_code": "print(0)", "mode": "sample"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("HTTP 403", response.json["error"])
        self.assertIn("blocked by network policy", response.json["error"])

    @patch("app.routes.coding._run_cases", return_value=(1,.01,None))
    def test_language_is_allowlisted_and_passed_to_runner(self, run):
        body={"problem_id":"maximum-segment-sum","source_code":"int main(){}","language":"cpp","mode":"sample"}
        self.assertEqual(self.one.post("/api/coding/submit",json=body).status_code,200)
        self.assertEqual(run.call_args.args[2],"cpp")
        self.assertEqual(self.one.post("/api/coding/submit",json={**body,"language":"ruby"}).status_code,400)
    def test_cpp_prefers_gcc_for_gnu_only_starter_header(self):
        from app.routes.coding import _choose_compiler
        compiler = _choose_compiler("cpp", [
            {"name": "clang-stable", "language": "C++"},
            {"name": "gcc-head", "language": "C++"},
            {"name": "gcc-stable", "language": "C++"},
        ])
        self.assertEqual(compiler["name"], "gcc-stable")

    @patch("app.routes.coding._run_custom_input", return_value={"status": "Executed", "accepted": True, "output": "0 1\n", "message": "Program finished successfully."})
    def test_custom_stdin_run_returns_terminal_output_without_saving_submission(self, run_custom):
        stdin = "5 9\n2 7 11 15 0\n"
        response = self.one.post("/api/coding/submit", json={
            "problem_id": "pair-target-indices", "source_code": "print('demo')",
            "language": "cpp", "mode": "custom", "stdin": stdin})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["result"]["output"], "0 1\n")
        self.assertEqual(run_custom.call_args.args, ("print('demo')", stdin, "cpp"))
        self.assertEqual(CodingSubmission.query.count(), 0)
        self.assertEqual(RewardTransaction.query.count(), 0)

    def test_custom_stdin_is_validated(self):
        response = self.one.post("/api/coding/submit", json={
            "problem_id": "pair-target-indices", "source_code": "print(1)",
            "mode": "custom", "stdin": "x" * 10001})
        self.assertEqual(response.status_code, 400)

    @patch("app.routes.coding._run_cases", side_effect=URLError("offline"))
    def test_outage_returns_actionable_message(self, _run):
        res=self.one.post("/api/coding/submit",json={"problem_id":"pair-target-indices","source_code":"print(0)","mode":"sample"})
        self.assertEqual(res.status_code,503); self.assertIn("internet",res.json["error"].lower()); self.assertIn("compiler",res.json["error"].lower())
    @patch("app.routes.coding._run_cases", return_value=(2,.02,{"status":"Wrong Answer","message":"Mismatch"}))
    def test_saved_attempt_isolated_and_readiness_uses_score(self, run):
        body={"problem_id":"pair-target-indices","source_code":"print('demo')","mode":"submit"}
        res=self.one.post("/api/coding/submit",json=body); self.assertFalse(res.json["result"]["accepted"])
        self.assertEqual(CodingSubmission.query.count(),1); self.assertEqual(self.two.get("/api/coding/history").json["submissions"],[])
        comp=next(x for x in build_readiness(1)["readiness"]["components"] if x["key"]=="C")
        self.assertEqual(comp["score"],40.0)
        from app.coding_bank import PROBLEM_BY_ID
        self.assertEqual(run.call_args.args[1],PROBLEM_BY_ID["pair-target-indices"]["tests"])
    @patch("app.routes.coding._run_cases", return_value=(1,.01,None))
    def test_sample_not_saved_and_invalid_payloads_rejected(self, _run):
        body={"problem_id":"first-target-position","source_code":"print(0)"}
        self.assertTrue(self.one.post("/api/coding/submit",json={**body,"mode":"sample"}).json["result"]["accepted"])
        self.assertEqual(CodingSubmission.query.count(),0); self.assertEqual(RewardTransaction.query.count(),0)
        self.assertEqual(self.one.post("/api/coding/submit",json={**body,"source_code":""}).status_code,400)
        self.assertEqual(self.one.post("/api/coding/submit",json={**body,"problem_id":"invalid"}).status_code,400)
    @patch("app.routes.coding._run_cases", return_value=(5,.03,None))
    def test_reward_awarded_only_once_for_accepted_problem(self, _run):
        body={"problem_id":"maximum-segment-sum","source_code":"print(1)"}
        first=self.one.post("/api/coding/submit",json=body).json["result"]
        second=self.one.post("/api/coding/submit",json=body).json["result"]
        self.assertIsNotNone(first["reward"]); self.assertNotIn("reward",second)
        self.assertEqual(RewardTransaction.query.filter_by(activity_type="coding_problem").count(),1)

if __name__ == "__main__": unittest.main()


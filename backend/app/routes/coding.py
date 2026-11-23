import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Blueprint, current_app, jsonify, request, session

from ..coding_bank import LANGUAGES, LANGUAGE_BY_ID, PROBLEMS, PROBLEM_BY_ID, starter_code
from ..extensions import db
from ..models import CodingSubmission, User
from ..services.gamification import award_activity

coding_bp = Blueprint("coding", __name__, url_prefix="/api/coding")
WANDBOX_API = "https://wandbox.org/api"
WANDBOX_LANGUAGE = {
    "python": "Python", "cpp": "C++", "java": "Java", "javascript": "JavaScript",
}
_compiler_catalog = {"loaded_at": 0.0, "items": []}


def _user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def _wandbox_request(path, payload=None, timeout=20):
    base_url = (current_app.config.get("WANDBOX_API_URL") or WANDBOX_API).rstrip("/")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(f"{base_url}{path}", data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Prepwise-CodingPractice/1.0"},
        method="POST" if data is not None else "GET")
    with urlopen(req, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not isinstance(result, (dict, list)):
        raise RuntimeError("The compiler service returned an invalid response.")
    return result


def _compilers():
    now = time.monotonic()
    if _compiler_catalog["items"] and now - _compiler_catalog["loaded_at"] < 3600:
        return _compiler_catalog["items"]
    items = _wandbox_request("/list.json", timeout=15)
    if not isinstance(items, list) or not items:
        raise RuntimeError("The compiler service returned an empty language list.")
    _compiler_catalog.update(loaded_at=now, items=items)
    return items


def _choose_compiler(language_key, compilers):
    wanted = WANDBOX_LANGUAGE[language_key]
    candidates = [item for item in compilers if isinstance(item, dict) and item.get("language") == wanted and item.get("name")]
    if not candidates:
        raise RuntimeError(f"The compiler service does not currently offer {wanted}.")

    def priority(item):
        name = item["name"].lower()
        head = "head" in name
        if language_key == "cpp":
            # The C++ starter uses GNU's bits/stdc++.h header.
            return (0 if "gcc" in name and not head else 1 if "gcc" in name else 2 if not head else 3, name)
        return (1 if head else 0, name)

    candidates.sort(key=priority)
    return candidates[0]


def _compiler_payload(language_key, source_code):
    compiler = _choose_compiler(language_key, _compilers())
    selected_options = []
    for switch in compiler.get("switches", []):
        if switch.get("default") is True:
            selected_options.append(switch.get("name", ""))
        elif isinstance(switch.get("default"), str) and switch["default"]:
            selected_options.append(switch["default"])
    return {"compiler": compiler["name"], "code": source_code,
        "options": ",".join(option for option in selected_options if option)}


def _clean_compiler_text(value):
    return re.sub(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", str(value or ""))


def _compile_once(source_code, input_data, language_key, payload_base=None):
    payload = payload_base or _compiler_payload(language_key, source_code)
    result = _wandbox_request("/compile.json", {**payload, "stdin": input_data}, timeout=25)
    if not isinstance(result, dict) or "status" not in result:
        raise RuntimeError("The compiler service returned a result without an exit status.")
    output = result.get("program_output")
    if output is None:
        output = result.get("program_message", "")
    return result, _clean_compiler_text(output)


def _run_custom_input(source_code, input_data, language_key):
    result, output = _compile_once(source_code, input_data, language_key)
    exit_code = str(result.get("status", ""))
    errors = _clean_compiler_text(result.get("compiler_error") or result.get("compiler_message") or "")
    runtime_error = _clean_compiler_text(result.get("program_error") or "")
    if exit_code == "0":
        return {"status": "Executed", "accepted": True, "output": output,
            "message": "Program finished successfully."}
    status = "Compilation Error" if errors else "Runtime Error" if result.get("signal") or runtime_error else "Execution Error"
    return {"status": status, "accepted": False, "output": output,
        "message": (errors or runtime_error or str(result.get("signal") or "Program exited with an error."))[:1200]}


def _run_cases(source_code, cases, language_key):
    payload_base = _compiler_payload(language_key, source_code)
    passed = 0
    max_time = 0.0
    failure = None
    for input_data, expected_output in cases:
        result, output = _compile_once(source_code, input_data, language_key, payload_base)
        status = str(result.get("status", ""))
        if status == "0" and output.strip() == expected_output.strip():
            passed += 1
        elif failure is None:
            compile_error = _clean_compiler_text(result.get("compiler_error") or result.get("compiler_message") or "")
            run_error = _clean_compiler_text(result.get("program_error") or result.get("program_message") or "")
            failure_status = "Compilation Error" if compile_error and status != "0" else (
                "Runtime Error" if result.get("signal") or run_error and status != "0" else "Wrong Answer")
            failure = {"status": failure_status,
                "message": str(compile_error or run_error or "The output did not match the expected result.")[:1200]}
        try:
            max_time = max(max_time, float(result.get("time") or 0))
        except (TypeError, ValueError):
            pass
    return passed, max_time, failure


@coding_bp.get("/problems")
def problems():
    if not _user():
        return jsonify(error="Authentication required."), 401
    language_id = request.args.get("language", "python")
    if language_id not in LANGUAGE_BY_ID:
        return jsonify(error="Choose a supported coding language."), 400
    safe = []
    for problem in PROBLEMS:
        item = {key: value for key, value in problem.items() if key not in ("tests", "starter_code")}
        item["starter_code"] = starter_code(problem["id"], language_id)
        safe.append(item)
    return jsonify(problems=safe, language=LANGUAGE_BY_ID[language_id]["label"],
        languages=[{"id": item["id"], "label": item["label"]} for item in LANGUAGES],
        source="Original demo exercises organized around Striver A2Z topic areas.")


@coding_bp.get("/history")
def history():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    rows = CodingSubmission.query.filter_by(user_id=user.id).order_by(
        CodingSubmission.created_at.desc(), CodingSubmission.id.desc()).limit(20).all()
    return jsonify(submissions=[{"id": row.id, "problem_id": row.problem_id,
        "title": PROBLEM_BY_ID.get(row.problem_id, {}).get("title", row.problem_id),
        "passed_tests": row.passed_tests, "total_tests": row.total_tests,
        "status": row.status, "language": LANGUAGE_BY_ID.get(row.language, {}).get("label", row.language),
        "created_at": row.created_at.isoformat().replace("+00:00", "Z")} for row in rows])


@coding_bp.post("/submit")
def submit():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Provide a code submission."), 400
    language_key = data.get("language", "python")
    if language_key not in LANGUAGE_BY_ID:
        return jsonify(error="Choose Python, C++, Java, or JavaScript."), 400
    problem = PROBLEM_BY_ID.get(data.get("problem_id"))
    if not problem:
        return jsonify(error="Choose one of the available demo problems."), 400
    source_code = data.get("source_code")
    if not isinstance(source_code, str) or not source_code.strip() or len(source_code) > 20000:
        return jsonify(error="Source code must contain 1 to 20,000 characters."), 400
    mode = data.get("mode", "submit")
    if mode not in ("sample", "submit", "custom"):
        return jsonify(error="Choose run with input, run example, or submit."), 400
    if mode == "custom":
        input_data = data.get("stdin", "")
        if not isinstance(input_data, str) or len(input_data) > 10000:
            return jsonify(error="Custom input must be text no longer than 10,000 characters."), 400
    else:
        cases = [(problem["sample_input"], problem["sample_output"])] if mode == "sample" else problem["tests"]
    try:
        if mode == "custom":
            custom_result = _run_custom_input(source_code, input_data, language_key)
        else:
            passed, run_time, failure = _run_cases(source_code, cases, language_key)
    except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        current_app.logger.warning("Wandbox request failed: %s", exc)
        if isinstance(exc, HTTPError) and exc.code in (401, 403):
            try:
                detail = exc.read(500).decode("utf-8", errors="replace").replace(chr(13), " ").replace(chr(10), " ")
            except Exception:
                detail = ""
            current_app.logger.warning("Wandbox denied %s (HTTP %s): %s", getattr(exc, "url", "request"), exc.code, detail[:300])
            detail = " ".join(re.sub(r"<[^>]*>", " ", detail).split())[:180]
            suffix = f" Details: {detail}" if detail else ""
            message = f"Wandbox refused this request (HTTP {exc.code}). The service or your network may be blocking code execution.{suffix}"
        elif isinstance(exc, HTTPError) and exc.code == 429:
            message = "The code runner is busy. Wait briefly and try again."
        elif isinstance(exc, HTTPError) and exc.code == 404:
            message = "The compiler service endpoint is unavailable. Check WANDBOX_API_URL in backend/.env."
        elif isinstance(exc, URLError):
            message = "Flask could not reach the online compiler. Check internet access and try again."
        elif isinstance(exc, TimeoutError):
            message = "The compiler took too long to respond. Try again with a smaller solution."
        else:
            message = "The compiler service returned an invalid result. Try again shortly."
        return jsonify(error=message), 503

    if mode == "custom":
        return jsonify(result={"mode": "custom", **custom_result})

    accepted = passed == len(cases)
    response = {"mode": mode, "passed_tests": passed, "total_tests": len(cases),
        "accepted": accepted, "status": "Accepted" if accepted else (failure or {}).get("status", "Wrong Answer"),
        "execution_time": round(run_time, 3),
        "message": "All tests passed." if accepted else (failure or {}).get("message", "The output did not match the expected result.")}
    if mode == "submit":
        row = CodingSubmission(user_id=user.id, problem_id=problem["id"], language=language_key,
            source_code=source_code, passed_tests=passed, total_tests=len(cases),
            status=response["status"], execution_time=run_time)
        db.session.add(row)
        db.session.flush()
        if accepted and not CodingSubmission.query.filter_by(user_id=user.id, problem_id=problem["id"],
                status="Accepted").filter(CodingSubmission.id != row.id).first():
            response["reward"] = award_activity(user.id, "coding_problem",
                PROBLEMS.index(problem) + 1, correct=1, total=1, topic=problem["topic"], answered=1)
        db.session.commit()
        response["submission_id"] = row.id
    return jsonify(result=response)



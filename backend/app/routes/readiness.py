import json
import re
from datetime import timezone

from flask import Blueprint, jsonify, request, session

from ..extensions import db
from ..models import PlacementReport, TargetCompanyPreference, User
from ..services.nemotron import NemotronClient, NemotronUnavailable
from ..services.readiness import build_readiness

readiness_bp = Blueprint("readiness", __name__, url_prefix="/api/readiness")


def _user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def _text(value, limit=700):
    if not isinstance(value, str):
        raise ValueError("Expected report text")
    value = re.sub(r"\s+", " ", value).strip()
    if not 8 <= len(value) <= limit:
        raise ValueError("Report text length is invalid")
    if re.search(r"\d|\b(?:guaranteed? job|job offer probability|certain to be hired|minimum score|cut.?off score|eligible for hire)\b", value, re.IGNORECASE):
        raise ValueError("Narrative must leave numeric facts to the application and avoid hiring claims")
    return value


def _fallback_narrative(snapshot):
    weak = snapshot["skill_gaps"]["weak_topics"]
    strengths = snapshot["strengths"]
    priorities = snapshot["recommendations"]
    analysis = []
    for item in weak[:6]:
        analysis.append({"label": f"{item['topic']} ({item['subject']})",
                         "guidance": f"Accuracy is {item['accuracy']}% across {item['attempted']} answered practice questions. Review the underlying concepts and retry a focused set."})
    for item in strengths[:3]:
        analysis.append({"label": item["subject"], "guidance": f"Recorded accuracy is {item['accuracy']}% across {item['attempted']} answered assessment and practice questions. Maintain it with mixed timed review."})
    if not analysis:
        analysis.append({"label": "Baseline", "guidance": "Complete an assessment and answer practice questions to create a data-based skill profile."})
    return {"summary": "This report uses your saved assessment and practice records. Categories without recorded evidence remain pending.",
            "assessment_analysis": (f"You have completed {snapshot['profile']['completed_assessments']} timed assessment(s) and "
                                    f"{snapshot['profile']['completed_practice_sessions']} practice session(s). The category scores and charts below are calculated from saved answers."),
            "skill_analysis": analysis,
            "recommendations": [item["action"] for item in priorities[:5]] or ["Complete a short assessment or practice set to establish a baseline."],
            "company_preparation": [{"company": item["company"], "guidance": item["guidance"]} for item in snapshot["company_recommendations"]]}


def _validate_narrative(value, snapshot):
    if not isinstance(value, dict):
        raise ValueError("Report response must be an object")
    raw_analysis = value.get("skill_analysis")
    raw_recommendations = value.get("recommendations")
    raw_companies = value.get("company_preparation")
    allowed = {f"{item['topic']} ({item['subject']})" for item in snapshot["topics"]}
    allowed.update(item["subject"] for item in snapshot["subjects"] if item["accuracy"] is not None)
    if not isinstance(raw_analysis, list) or not 1 <= len(raw_analysis) <= 10:
        raise ValueError("Skill analysis list is invalid")
    normalized_analysis, seen = [], set()
    for item in raw_analysis:
        if not isinstance(item, dict) or item.get("label") not in allowed | {"Baseline"} or item["label"] in seen:
            raise ValueError("Skill analysis references unknown data")
        seen.add(item["label"])
        normalized_analysis.append({"label": item["label"], "guidance": _text(item.get("guidance"), 500)})
    if not isinstance(raw_recommendations, list) or not 1 <= len(raw_recommendations) <= 6:
        raise ValueError("Recommendation list is invalid")
    recommendations = [_text(item, 300) for item in raw_recommendations]
    if not isinstance(raw_companies, list) or len(raw_companies) != len(snapshot["target_companies"]):
        raise ValueError("Company recommendation list is invalid")
    companies = []
    expected = set(snapshot["target_companies"])
    seen_companies = set()
    for item in raw_companies:
        if not isinstance(item, dict) or item.get("company") not in expected or item.get("company") in seen_companies:
            raise ValueError("Company recommendation references an unselected company")
        seen_companies.add(item["company"])
        guidance = _text(item.get("guidance"), 500)
        if re.search(r"\b(?:hiring requirement|eligibility requirement|minimum GPA|selection criteria|guaranteed interview)\b", guidance, re.IGNORECASE):
            raise ValueError("Company guidance cannot assert hiring requirements")
        companies.append({"company": item["company"], "guidance": guidance})
    if seen_companies != expected:
        raise ValueError("Company recommendations must cover each selected company once")
    return {"summary": _text(value.get("summary"), 900),
            "assessment_analysis": _text(value.get("assessment_analysis"), 900),
            "skill_analysis": normalized_analysis, "recommendations": recommendations,
            "company_preparation": companies}


def _report_dict(row):
    created = row.created_at.replace(tzinfo=timezone.utc) if row.created_at.tzinfo is None else row.created_at.astimezone(timezone.utc)
    return {"id": row.id, "created_at": created.isoformat().replace("+00:00", "Z"), "source": row.source,
            "snapshot": row.data_snapshot, "narrative": row.narrative}


@readiness_bp.get("")
def get_readiness():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    return jsonify(build_readiness(user.id))


@readiness_bp.put("/companies")
def save_companies():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("companies"), list) or len(data["companies"]) > 5:
        return jsonify(error="Provide a list of up to five target companies."), 400
    companies, seen = [], set()
    for item in data["companies"]:
        if not isinstance(item, str):
            return jsonify(error="Company names must be text."), 400
        name = re.sub(r"\s+", " ", item).strip()
        if not 2 <= len(name) <= 80:
            return jsonify(error="Company names must be between 2 and 80 characters."), 400
        key = name.casefold()
        if key not in seen:
            companies.append(name)
            seen.add(key)
    TargetCompanyPreference.query.filter_by(user_id=user.id).delete()
    db.session.add_all(TargetCompanyPreference(user_id=user.id, company_name=name) for name in companies)
    db.session.commit()
    return jsonify(companies=companies)


@readiness_bp.get("/report")
def latest_report():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    row = PlacementReport.query.filter_by(user_id=user.id).order_by(PlacementReport.created_at.desc(), PlacementReport.id.desc()).first()
    return jsonify(report=_report_dict(row) if row else None)


@readiness_bp.post("/report")
def create_report():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    snapshot = build_readiness(user.id)
    ai_context = dict(snapshot)
    ai_context["profile"] = {key: value for key, value in snapshot["profile"].items() if key not in ("name", "member_since")}
    source = "nemotron"
    try:
        prompt = [
            {"role": "system", "content": (
                "You write a placement preparation report from the supplied, de-identified application data. "
                "Do not calculate, change, or infer scores; do not invent performance, coding ability, experience, "
                "hiring requirements, or company-specific eligibility. Treat all unavailable score components as pending. "
                "Give general preparation guidance for the selected companies and advise checking official role information. "
                "Return JSON only with keys summary, assessment_analysis, skill_analysis, recommendations, company_preparation. "
                "skill_analysis must use labels exactly from the supplied subject/topic labels. company_preparation must use each selected company name exactly once."
            )},
            {"role": "user", "content": "Create concise supportive explanations from this actual performance snapshot. Do not repeat a job-probability claim.\n" + json.dumps(ai_context, ensure_ascii=False)},
        ]
        narrative = _validate_narrative(NemotronClient().complete_json(prompt, max_tokens=1600), snapshot)
    except (NemotronUnavailable, ValueError, TypeError):
        source = "fallback"
        narrative = _fallback_narrative(snapshot)
    row = PlacementReport(user_id=user.id, data_snapshot=snapshot, narrative=narrative, source=source)
    db.session.add(row)
    db.session.commit()
    return jsonify(report=_report_dict(row)), 201

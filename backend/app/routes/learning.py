import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from ..extensions import db
from ..models import LearningNotification, StudentProfile, TargetCompanyPreference, User
from ..services.learning import (
    complete_plan_task, get_or_create_plan, goals_payload, missions_payload,
    notifications_payload, profile_payload,
)

learning_bp = Blueprint("learning", __name__, url_prefix="/api/learning")


def _user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def _list(value, label, maximum=20):
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, list):
        values = value
    else:
        raise ValueError(f"{label} must be a list or comma-separated text.")
    result, seen = [], set()
    for item in values:
        if not isinstance(item, str):
            raise ValueError(f"{label} entries must be text.")
        item = re.sub(r"\s+", " ", item).strip()
        if not item:
            continue
        if len(item) > 80:
            raise ValueError(f"Each {label.lower()} entry must be 80 characters or fewer.")
        if item.casefold() not in seen:
            result.append(item)
            seen.add(item.casefold())
    if len(result) > maximum:
        raise ValueError(f"Provide no more than {maximum} {label.lower()} entries.")
    return result


def _clean_text(value, label, limit):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > limit:
        raise ValueError(f"{label} must be {limit} characters or fewer.")
    return value or None


@learning_bp.get("/profile")
def get_profile():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    return jsonify(profile=profile_payload(user.id), account={"name": user.name, "email": user.email})


@learning_bp.put("/profile")
def save_profile():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Provide profile details."), 400
    try:
        row = StudentProfile.query.filter_by(user_id=user.id).first() or StudentProfile(user_id=user.id)
        row.college = _clean_text(data.get("college", row.college), "College/university", 160)
        row.degree = _clean_text(data.get("degree", row.degree), "Degree", 100)
        row.department = _clean_text(data.get("department", row.department), "Department", 100)
        year = data.get("graduation_year", row.graduation_year)
        if year in (None, ""):
            row.graduation_year = None
        elif not isinstance(year, int) or isinstance(year, bool) or year < 2000 or year > 2100:
            raise ValueError("Graduation year must be between 2000 and 2100.")
        else:
            row.graduation_year = year
        cgpa = data.get("cgpa", row.cgpa)
        if cgpa in (None, ""):
            row.cgpa = None
        else:
            try:
                cgpa = float(cgpa)
            except (TypeError, ValueError):
                raise ValueError("CGPA must be a number between 0 and 10.")
            if not 0 <= cgpa <= 10:
                raise ValueError("CGPA must be a number between 0 and 10.")
            row.cgpa = cgpa
        row.technical_skills = _list(data.get("technical_skills", row.technical_skills or []), "Technical skills")
        row.programming_languages = _list(data.get("programming_languages", row.programming_languages or []), "Programming languages")
        row.target_roles = _list(data.get("target_roles", row.target_roles or []), "Target roles", 10)
        row.preferred_language = _clean_text(data.get("preferred_language", row.preferred_language), "Preferred language", 60)
        daily = data.get("daily_study_target", row.daily_study_target)
        weekly = data.get("weekly_study_target", row.weekly_study_target)
        if not isinstance(daily, int) or isinstance(daily, bool) or not 15 <= daily <= 1440:
            raise ValueError("Daily study target must be between 15 and 1440 minutes.")
        if not isinstance(weekly, int) or isinstance(weekly, bool) or not daily <= weekly <= 10080:
            raise ValueError("Weekly study target must be at least the daily target and at most 10080 minutes.")
        row.daily_study_target, row.weekly_study_target = daily, weekly
        companies = _list(data.get("target_companies", [item.company_name for item in TargetCompanyPreference.query.filter_by(user_id=user.id).all()]),
                          "Target companies", 5)
        TargetCompanyPreference.query.filter_by(user_id=user.id).delete()
        db.session.add_all(TargetCompanyPreference(user_id=user.id, company_name=name) for name in companies)
        db.session.add(row)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        return jsonify(error=str(error)), 400
    return jsonify(profile=profile_payload(user.id))


@learning_bp.get("/plan")
def daily_plan():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    plan = get_or_create_plan(user.id)
    db.session.commit()
    return jsonify(plan=plan)


@learning_bp.post("/plan/tasks/<int:task_id>/complete")
def complete_task(task_id):
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    task = complete_plan_task(user.id, task_id)
    if not task:
        return jsonify(error="Plan task not found."), 404
    return jsonify(task=task)


@learning_bp.get("/missions")
def get_missions():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    return jsonify(missions=missions_payload(user.id))


@learning_bp.get("/goals")
def get_goals():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    return jsonify(goals=goals_payload(user.id))


@learning_bp.get("/notifications")
def get_notifications():
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    return jsonify(notifications=notifications_payload(user.id),
                   unread_count=LearningNotification.query.filter_by(user_id=user.id, read_at=None).count())


@learning_bp.post("/notifications/<int:notification_id>/read")
def mark_notification_read(notification_id):
    user = _user()
    if not user:
        return jsonify(error="Authentication required."), 401
    row = LearningNotification.query.filter_by(id=notification_id, user_id=user.id).first()
    if not row:
        return jsonify(error="Notification not found."), 404
    if row.read_at is None:
        row.read_at = datetime.now(timezone.utc)
        db.session.commit()
    return jsonify(notification={"id": row.id, "read": True})

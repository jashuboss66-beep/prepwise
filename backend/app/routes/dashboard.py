from flask import Blueprint, jsonify, session

from ..extensions import db
from ..models import User

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("")
def dashboard():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        return jsonify(error="Authentication required."), 401
    return jsonify(user=user.to_dict(), message="Your preparation workspace is ready.")

from flask import Blueprint, jsonify, session
from ..extensions import db
from ..models import User
from ..services.gamification import gamification_dashboard

gamification_bp = Blueprint("gamification", __name__, url_prefix="/api/gamification")

@gamification_bp.get("")
def dashboard():
    user_id = session.get("user_id")
    if not user_id or not db.session.get(User, user_id):
        return jsonify(error="Authentication required."), 401
    return jsonify(gamification_dashboard(user_id))

import re

from flask import Blueprint, jsonify, request, session
from sqlalchemy import func

from ..extensions import db
from ..models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if len(name) < 2 or len(name) > 80:
        return jsonify(error="Name must be between 2 and 80 characters."), 400
    if not EMAIL_RE.match(email):
        return jsonify(error="Enter a valid email address."), 400
    if len(password) < 8:
        return jsonify(error="Password must be at least 8 characters."), 400
    if User.query.filter(func.lower(User.email) == email).first():
        return jsonify(error="An account with this email already exists."), 409

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    session.clear()
    session["user_id"] = user.id
    return jsonify(user=user.to_dict()), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    user = User.query.filter(func.lower(User.email) == email).first()
    if not user or not user.check_password(password):
        return jsonify(error="Email or password is incorrect."), 401
    session.clear()
    session["user_id"] = user.id
    return jsonify(user=user.to_dict())


@auth_bp.get("/me")
def me():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        session.clear()
        return jsonify(error="Authentication required."), 401
    return jsonify(user=user.to_dict())


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify(message="Signed out.")

import os
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy import inspect, text

from .extensions import db
from .models import Question
from .question_bank import seed_question_bank
from .routes.assessments import assessments_bp
from .routes.ai import ai_bp
from .routes.auth import auth_bp
from .routes.dashboard import dashboard_bp
from .routes.practice import practice_bp
from .routes.gamification import gamification_bp
from .routes.readiness import readiness_bp
from .routes.learning import learning_bp
from .routes.placement_hub import hub_bp
from .routes.coding import coding_bp


def create_app(test_config=None):
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    app = Flask(__name__, instance_relative_config=True)
    database_path = Path(app.instance_path) / "placement_prep.sqlite3"
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "local-prototype-change-this-secret"),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path.as_posix()}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
    )
    if test_config:
        app.config.update(test_config)
    try:
        cutoff_hour = int(os.environ.get("DAILY_QUIZ_CUTOFF_UTC_HOUR", "23"))
        app.config["DAILY_QUIZ_CUTOFF_UTC_HOUR"] = cutoff_hour if 0 <= cutoff_hour <= 23 else 23
    except ValueError:
        app.config["DAILY_QUIZ_CUTOFF_UTC_HOUR"] = 23

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
    CORS(app, supports_credentials=True, origins=[frontend_origin])
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(assessments_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(practice_bp)
    app.register_blueprint(gamification_bp)
    app.register_blueprint(readiness_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(hub_bp)
    app.register_blueprint(coding_bp)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    with app.app_context():
        db.create_all()
        additions = {
            "question": {
                "topic": "VARCHAR(80) NOT NULL DEFAULT 'General'",
                "difficulty": "VARCHAR(20) NOT NULL DEFAULT 'medium'",
                "practice_only": "BOOLEAN NOT NULL DEFAULT 0",
                "category": "VARCHAR(40) NOT NULL DEFAULT 'Legacy'",
                "source": "VARCHAR(120) NOT NULL DEFAULT 'Original: Prepwise project'",
                "license": "VARCHAR(120) NOT NULL DEFAULT 'Project original content'",
                "reference_url": "VARCHAR(500)",
            },
            "practice_session": {
                "mode": "VARCHAR(20) NOT NULL DEFAULT 'normal'",
                "quiz_date": "DATE",
            },
            "assessment_attempt": {
                "assessment_mode": "VARCHAR(20) NOT NULL DEFAULT 'initial'",
                "assessment_category": "VARCHAR(40)",
                "difficulty": "VARCHAR(20)",
            },
            "assessment_attempt_question": {
                "option_order": "JSON NOT NULL DEFAULT '[0,1,2,3]'",
                "first_viewed_at": "DATETIME",
            },
            "assessment_answer": {"time_spent_seconds": "INTEGER"},
        }
        with db.engine.begin() as connection:
            for table, fields in additions.items():
                columns = {column["name"] for column in inspect(db.engine).get_columns(table)}
                for name, declaration in fields.items():
                    if name not in columns:
                        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}"))
        seed_question_bank(Question)
        from .services.adaptive import tag_question_bank
        tag_question_bank(Question)

    return app

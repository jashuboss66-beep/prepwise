from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from ..extensions import db
from ..models import (AssessmentAnswer, AssessmentAttempt, CodingSubmission, PracticeAttempt, PracticeSession,
                      Question, TargetCompanyPreference, User)

WEIGHTS = {"A": 0.25, "T": 0.25, "C": 0.25, "M": 0.15, "S": 0.10}
NAMES = {"A": "Aptitude", "T": "Technical", "C": "Coding", "M": "Mock assessment", "S": "Learning consistency"}
SUBJECT_NAMES = ("Aptitude", "Logical Reasoning", "Verbal Ability", "Technical")


def _accuracy(correct, attempted):
    return round(correct * 100 / attempted, 1) if attempted else None


def _answered_assessment_rows(user_id):
    rows = (db.session.query(AssessmentAttempt, AssessmentAnswer, Question)
        .join(AssessmentAnswer, AssessmentAnswer.attempt_id == AssessmentAttempt.id)
        .join(Question, Question.id == AssessmentAnswer.question_id)
        .filter(AssessmentAttempt.user_id == user_id, AssessmentAttempt.completed_at.isnot(None),
                AssessmentAnswer.selected_option.isnot(None))
        .order_by(AssessmentAttempt.completed_at, AssessmentAnswer.id).all())
    return rows


def _performance_events(user_id):
    events = []
    attempts = AssessmentAttempt.query.filter_by(user_id=user_id).filter(AssessmentAttempt.completed_at.isnot(None)).order_by(AssessmentAttempt.completed_at).all()
    for attempt in attempts:
        answered = AssessmentAnswer.query.filter_by(attempt_id=attempt.id).filter(AssessmentAnswer.selected_option.isnot(None)).all()
        if answered:
            events.append({"date": attempt.completed_at.isoformat(), "label": "Assessment", "score": _accuracy(sum(int(row.is_correct) for row in answered), len(answered)), "type": "assessment"})
    sessions = PracticeSession.query.filter_by(user_id=user_id).filter(PracticeSession.completed_at.isnot(None)).order_by(PracticeSession.completed_at).all()
    for item in sessions:
        answered = PracticeAttempt.query.filter_by(user_id=user_id, session_id=item.id).filter(PracticeAttempt.selected_option.isnot(None)).all()
        if answered:
            events.append({"date": item.completed_at.isoformat(), "label": item.topic or item.subject, "score": _accuracy(sum(int(row.is_correct) for row in answered), len(answered)), "type": "practice"})
    events.sort(key=lambda row: row["date"])
    return events[-30:]


def build_readiness(user_id, today=None):
    today = today or datetime.now(timezone.utc).date()
    user = db.session.get(User, user_id)
    assessments = AssessmentAttempt.query.filter_by(user_id=user_id).filter(AssessmentAttempt.completed_at.isnot(None)).order_by(AssessmentAttempt.completed_at.asc()).all()
    practice_sessions = PracticeSession.query.filter_by(user_id=user_id).filter(PracticeSession.completed_at.isnot(None)).order_by(PracticeSession.completed_at.asc()).all()
    assessment_rows = _answered_assessment_rows(user_id)
    practice_rows = PracticeAttempt.query.filter_by(user_id=user_id).filter(PracticeAttempt.selected_option.isnot(None)).order_by(PracticeAttempt.attempted_at.asc()).all()
    coding_rows = CodingSubmission.query.filter_by(user_id=user_id).order_by(CodingSubmission.created_at.asc()).all()

    subject_counts = defaultdict(lambda: {"correct": 0, "attempted": 0})
    for _, answer, question in assessment_rows:
        subject_counts[question.subject]["attempted"] += 1
        subject_counts[question.subject]["correct"] += int(answer.is_correct)
    for row in practice_rows:
        subject_counts[row.subject]["attempted"] += 1
        subject_counts[row.subject]["correct"] += int(row.is_correct)
    subjects = [{"subject": name, "attempted": subject_counts[name]["attempted"],
                 "correct": subject_counts[name]["correct"],
                 "accuracy": _accuracy(subject_counts[name]["correct"], subject_counts[name]["attempted"])}
                for name in SUBJECT_NAMES]

    category_data = {
        "A": subject_counts["Aptitude"],
        "T": subject_counts["Technical"],
    }
    best_coding_by_problem = {}
    for row in coding_rows:
        ratio = row.passed_tests / row.total_tests if row.total_tests else 0
        if row.problem_id not in best_coding_by_problem or ratio > best_coding_by_problem[row.problem_id]:
            best_coding_by_problem[row.problem_id] = ratio
    coding_score = round(sum(best_coding_by_problem.values()) * 100 / len(best_coding_by_problem), 1) if best_coding_by_problem else None
    attempted_assessment = 0
    correct_assessment = 0
    for attempt in assessments:
        answers = [row for row in assessment_rows if row[0].id == attempt.id]
        attempted_assessment += len(answers)
        correct_assessment += sum(int(answer.is_correct) for _, answer, _ in answers)
    mock_score = _accuracy(correct_assessment, attempted_assessment)

    active_dates = set()
    for attempt in assessments:
        answers = AssessmentAnswer.query.filter_by(attempt_id=attempt.id).filter(AssessmentAnswer.selected_option.isnot(None)).count()
        if answers >= max(1, (attempt.total_questions + 1) // 2):
            value = attempt.completed_at
            active_dates.add(value.date() if value.tzinfo else value.date())
    practice_by_session = defaultdict(list)
    for row in PracticeAttempt.query.filter_by(user_id=user_id).all():
        practice_by_session[row.session_id].append(row)
    for item in practice_sessions:
        answers = [row for row in practice_by_session[item.id] if row.selected_option is not None]
        if answers and len(answers) >= max(1, (len(practice_by_session[item.id]) + 1) // 2):
            value = item.completed_at
            active_dates.add(value.date() if value.tzinfo else value.date())
    active_days_30 = sum(today - timedelta(days=29) <= day <= today for day in active_dates)
    consistency_score = round(min(100, active_days_30 * 5), 1) if active_days_30 else None

    components = []
    raw = {"A": _accuracy(category_data["A"]["correct"], category_data["A"]["attempted"]),
           "T": _accuracy(category_data["T"]["correct"], category_data["T"]["attempted"]),
           "C": coding_score, "M": mock_score, "S": consistency_score}
    for key in WEIGHTS:
        score = raw[key]
        evidence = {"A": f"{category_data['A']['attempted']} answered aptitude items across assessment and practice",
                    "T": f"{category_data['T']['attempted']} answered technical items across assessment and practice",
                    "C": f"Best test-case pass rate on {len(best_coding_by_problem)} coding problem(s), one best attempt per problem" if best_coding_by_problem else "No coding-task submissions are recorded yet.",
                    "M": f"{len(assessments)} completed timed placement assessment(s), used as the mock-assessment proxy; based on {attempted_assessment} answered items",
                    "S": f"{active_days_30} meaningful learning days in the last 30 days (5 points per day, capped at 20 days)"}[key]
        components.append({"key": key, "name": NAMES[key], "weight": WEIGHTS[key], "score": score,
                           "status": "available" if score is not None else "pending", "evidence": evidence})
    available = [component for component in components if component["score"] is not None]
    weight_total = sum(item["weight"] for item in available)
    readiness_score = round(sum(item["weight"] * item["score"] for item in available) / weight_total, 1) if weight_total else None

    topic_groups = defaultdict(list)
    for _, answer, question in assessment_rows:
        topic_groups[(question.subject, question.topic)].append((answer.answered_at, bool(answer.is_correct)))
    for row in practice_rows:
        topic_groups[(row.subject, row.topic)].append((row.attempted_at, bool(row.is_correct)))
    topics = []
    for (subject, topic), rows in sorted(topic_groups.items()):
        correct = sum(int(is_correct) for _, is_correct in rows)
        ordered = sorted(rows, key=lambda row: row[0])
        recent = ordered[-5:]
        previous = ordered[-10:-5]
        improvement = None
        if len(recent) >= 2 and len(previous) >= 2:
            improvement = round(_accuracy(sum(int(is_correct) for _, is_correct in recent), len(recent)) -
                                _accuracy(sum(int(is_correct) for _, is_correct in previous), len(previous)), 1)
        accuracy = _accuracy(correct, len(rows))
        topics.append({"subject": subject, "topic": topic, "attempted": len(rows), "correct": correct,
                       "mastery": accuracy, "accuracy": accuracy, "improvement": improvement,
                       "status": "immediate" if accuracy < 50 else "improve" if accuracy < 70 else "on_track"})
    weak_subjects = [row for row in subjects if row["accuracy"] is not None and row["accuracy"] < 60]
    weak_topics = [row for row in topics if row["accuracy"] < 70]
    strongest = sorted((row for row in subjects if row["accuracy"] is not None), key=lambda row: (-row["accuracy"], row["subject"]))[:3]
    weakest = sorted((row for row in subjects if row["accuracy"] is not None), key=lambda row: (row["accuracy"], row["subject"]))[:3]
    improved_topics = sorted((row for row in topics if row["improvement"] is not None and row["improvement"] > 0),
                             key=lambda row: -row["improvement"])
    immediate = sorted((row for row in topics if row["accuracy"] < 50), key=lambda row: (row["accuracy"], row["topic"]))

    events = _performance_events(user_id)
    performance_change = None
    if len(events) >= 2:
        recent = events[-5:]
        prior = events[-10:-5]
        if prior:
            recent_avg = sum(row["score"] for row in recent) / len(recent)
            prior_avg = sum(row["score"] for row in prior) / len(prior)
            delta = round(recent_avg - prior_avg, 1)
            performance_change = {"delta": delta, "direction": "up" if delta > 0 else "down" if delta < 0 else "stable",
                                  "recent_average": round(recent_avg, 1), "previous_average": round(prior_avg, 1)}
        else:
            performance_change = {"delta": None, "direction": "baseline", "recent_average": round(sum(row["score"] for row in recent) / len(recent), 1), "previous_average": None}

    start_day = today - timedelta(days=13)
    practice_daily = defaultdict(int)
    for item in practice_sessions:
        when = item.completed_at.date()
        if start_day <= when <= today:
            rows = practice_by_session[item.id]
            practice_daily[when.isoformat()] += len([row for row in rows if row.selected_option is not None])
    practice_activity = [{"date": (start_day + timedelta(days=index)).isoformat(), "answered": practice_daily[(start_day + timedelta(days=index)).isoformat()]}
                         for index in range(14)]
    difficulty = {key: sum(row.difficulty == key for row in practice_rows) for key in ("easy", "medium", "hard")}

    companies = [row.company_name for row in TargetCompanyPreference.query.filter_by(user_id=user_id).order_by(TargetCompanyPreference.company_name).all()]
    recommendations = []
    for row in immediate[:3] + [topic for topic in weak_topics if topic not in immediate][:3]:
        recommendations.append({"priority": "Immediate" if row["accuracy"] < 50 else "Next", "subject": row["subject"],
                                "topic": row["topic"], "reason": f"Recorded accuracy is {row['accuracy']}% across {row['attempted']} answered assessment and practice questions.",
                                "action": f"Review {row['topic']} fundamentals, then complete a focused practice set."})
    for row in weakest:
        if row["accuracy"] < 60 and not any(item["subject"] == row["subject"] for item in recommendations):
            recommendations.append({"priority": "Next", "subject": row["subject"], "topic": None,
                                    "reason": f"Combined assessment and practice accuracy is {row['accuracy']}% across {row['attempted']} answers.",
                                    "action": f"Review missed {row['subject']} questions and practice in short untimed sets."})
    if not recommendations and not any(item["accuracy"] is not None for item in subjects):
        recommendations.append({"priority": "Start", "subject": None, "topic": None,
                                "reason": "No completed, answered assessment or practice records are available yet.",
                                "action": "Complete the initial assessment or a practice session to establish a baseline."})
    focus_text = ", ".join(f"{item['topic']} ({item['subject']})" for item in recommendations[:2])
    company_recommendations = [{"company": name,
        "guidance": (f"Prioritize your recorded improvement areas in {focus_text}. " if focus_text else "Maintain your current skills and complete more practice to establish clearer priorities. ") +
                    "Compare your current skills with the role description you are targeting, prepare project explanations, and review the company's official careers information for current roles and process. This is general preparation guidance, not a statement of hiring requirements."}
        for name in companies]

    completed_answer_count = sum(1 for _, answer, _ in assessment_rows) + len(practice_rows)
    return {
        "profile": {"name": user.name, "member_since": user.created_at.isoformat(),
                    "completed_assessments": len(assessments), "completed_practice_sessions": len(practice_sessions),
                    "answered_questions": completed_answer_count},
        "readiness": {"score": readiness_score, "status": "pending" if readiness_score is None else "partial" if weight_total < 1 else "available",
                      "components": components, "available_weight": round(weight_total, 2),
                      "formula": "R = (0.25A + 0.25T + 0.25C + 0.15M + 0.10S) / sum of weights for available components",
                      "interpretation": "A preparation progress indicator based on recorded activity; it is not a probability of receiving a job offer."},
        "subjects": subjects, "topics": topics,
        "skill_gaps": {"weak_topics": weak_topics, "weak_subjects": weak_subjects,
                       "improved_topics": improved_topics, "immediate_attention": immediate},
        "strengths": strongest, "weaknesses": weakest,
        "recommendations": recommendations,
        "recent_performance_change": performance_change,
        "analytics": {"subject_performance": subjects,
                      "mastery_radar": [{"topic": row["topic"], "subject": row["subject"], "mastery": row["mastery"]} for row in topics],
                      "accuracy_trend": events,
                      "practice_activity": practice_activity,
                      "difficulty_distribution": difficulty},
        "target_companies": companies, "company_recommendations": company_recommendations,
    }

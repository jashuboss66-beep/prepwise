from collections import defaultdict

from ..extensions import db
from ..models import AssessmentAttempt, AssessmentSubjectResult, PracticeAttempt, Question

TOPICS = {
    "Aptitude": ["Percentages", "Profit and Loss", "Simple and Compound Interest", "Time and Work",
                 "Time, Speed and Distance", "Averages", "Ratio and Proportion", "Probability",
                 "Permutations and Combinations", "Number Systems", "HCF and LCM", "Problems on Ages",
                 "Mixtures and Allegations", "Pipes and Cisterns", "Data Interpretation", "Simplification"],
    "Logical Reasoning": ["Number Sequences", "Syllogisms", "Directions", "Analogies", "Coding Patterns"],
    "Verbal Ability": ["Grammar", "Vocabulary", "Synonyms and Antonyms", "Sentence Correction", "Sentence Completion",
                       "Error Identification", "Para Jumbles", "Reading Comprehension", "Verbal Reasoning",
                       "Business Communication", "Professional Email Writing", "Workplace Communication", "Interview Communication"],
    "Technical": ["C Programming", "C++", "Python", "Java", "Object-Oriented Programming",
                   "Data Structures and Algorithms", "DBMS", "SQL", "Operating Systems", "Computer Networks",
                   "Software Engineering", "Computer Fundamentals"],
}
DIFFICULTIES = ("easy", "medium", "hard")


def tag_question_bank(Question):
    for subject, topics in TOPICS.items():
        rows = Question.query.filter_by(subject=subject, topic="General").order_by(Question.id).all()
        for index, question in enumerate(rows):
            question.topic = topics[index % len(topics)]
            question.difficulty = ("easy", "medium", "hard", "medium", "easy")[index % 5]
    db.session.commit()


def user_attempts(user_id):
    return PracticeAttempt.query.filter_by(user_id=user_id).order_by(PracticeAttempt.attempted_at.desc(), PracticeAttempt.id.desc()).all()


def mastery_snapshot(user_id):
    rows = user_attempts(user_id)
    grouped = defaultdict(list)
    subject_groups = defaultdict(list)
    difficulty_counts = defaultdict(lambda: {level: 0 for level in DIFFICULTIES})
    for row in rows:
        grouped[(row.subject, row.topic)].append(row)
        subject_groups[row.subject].append(row)
        difficulty_counts[row.subject][row.difficulty] += 1
    topics = []
    for (subject, topic), attempts in sorted(grouped.items()):
        correct = sum(int(item.is_correct) for item in attempts)
        accuracy = round(correct * 100 / len(attempts), 1)
        recent = attempts[:5]
        recent_accuracy = round(sum(int(item.is_correct) for item in recent) * 100 / len(recent), 1)
        topics.append({"subject": subject, "topic": topic, "attempted": len(attempts), "correct": correct,
                       "accuracy": accuracy, "recent_accuracy": recent_accuracy, "mastery": accuracy,
                       "recommended": accuracy < 70, "difficulty_counts": _topic_difficulties(attempts)})
    subjects = []
    for subject in TOPICS:
        attempts = subject_groups.get(subject, [])
        if attempts:
            accuracy = round(sum(int(row.is_correct) for row in attempts) * 100 / len(attempts), 1)
            subjects.append({"subject": subject, "attempted": len(attempts), "correct": sum(int(row.is_correct) for row in attempts),
                             "accuracy": accuracy, "difficulty_counts": difficulty_counts[subject]})
        else:
            # Assessment data is a real baseline, but does not count as practice attempts.
            baseline = (db.session.query(AssessmentSubjectResult).join(
                AssessmentAttempt, AssessmentSubjectResult.attempt_id == AssessmentAttempt.id
            ).filter(AssessmentAttempt.user_id == user_id, AssessmentSubjectResult.subject == subject)
             .order_by(AssessmentAttempt.completed_at.desc()).first())
            subjects.append({"subject": subject, "attempted": 0, "correct": 0,
                             "accuracy": baseline.score_percent if baseline else None,
                             "baseline": bool(baseline), "difficulty_counts": difficulty_counts[subject]})
    recommendations = sorted(topics, key=lambda item: (item["accuracy"], -item["attempted"], item["topic"]))[:3]
    if not recommendations:
        measured = sorted((item for item in subjects if item["accuracy"] is not None), key=lambda item: item["accuracy"])
        subjects_to_start = measured[:3] if measured else subjects[:3]
        recommendations = [{"subject": item["subject"], "topic": TOPICS[item["subject"]][0],
                            "accuracy": item["accuracy"], "attempted": 0, "recommended": True,
                            "reason": "Subject baseline from the latest assessment." if item["accuracy"] is not None else "Start with a short practice set."}
                           for item in subjects_to_start]
    daily = defaultdict(lambda: {"attempted": 0, "correct": 0})
    for row in reversed(rows):
        day = row.attempted_at.date().isoformat()
        daily[day]["attempted"] += 1
        daily[day]["correct"] += int(row.is_correct)
    accuracy_trend = [{"date": day, "attempted": values["attempted"], "accuracy": round(values["correct"] * 100 / values["attempted"], 1)}
                      for day, values in sorted(daily.items())]
    return {"topics": topics, "subjects": subjects, "recommendations": recommendations,
            "total_attempts": len(rows), "available_topics": TOPICS,
            "recent": [_attempt_dict(row) for row in rows[:10]],
            "accuracy_trend": accuracy_trend[-14:],
            "difficulty_progression": [{"subject": subject, "counts": difficulty_counts[subject]} for subject in TOPICS]}


def _topic_difficulties(attempts):
    return {level: sum(item.difficulty == level for item in attempts) for level in DIFFICULTIES}


def _attempt_dict(row):
    return {"subject": row.subject, "topic": row.topic, "difficulty": row.difficulty,
            "is_correct": bool(row.is_correct), "attempted_at": row.attempted_at.isoformat()}


def choose_difficulty(user_id, subject, topic=None):
    query = PracticeAttempt.query.filter_by(user_id=user_id, subject=subject)
    if topic:
        query = query.filter_by(topic=topic)
    rows = query.order_by(PracticeAttempt.attempted_at.desc(), PracticeAttempt.id.desc()).limit(5).all()
    if len(rows) < 3:
        return "easy"
    accuracy = sum(int(row.is_correct) for row in rows) / len(rows)
    if accuracy >= .8:
        return "hard"
    if accuracy <= .4:
        return "easy"
    return "medium"


def pick_questions(user_id, subject, topic=None, limit=5):
    target = choose_difficulty(user_id, subject, topic)
    query = Question.query.filter_by(subject=subject)
    if topic:
        query = query.filter_by(topic=topic)
    pool = query.order_by(Question.id).all()
    if not pool:
        return [], target
    seen = {row.question_id for row in PracticeAttempt.query.filter_by(user_id=user_id).all()}
    unseen = [question for question in pool if question.id not in seen]
    candidates = unseen or pool
    # Prefer questions at target difficulty; when the small local bank has none, use closest difficulty.
    tier = {"easy": 0, "medium": 1, "hard": 2}
    candidates.sort(key=lambda question: (abs(tier[question.difficulty] - tier[target]), question.id))
    return candidates[:min(limit, len(candidates))], target

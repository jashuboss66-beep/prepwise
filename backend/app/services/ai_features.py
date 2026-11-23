import re


SUBJECTS = ("Aptitude", "Logical Reasoning", "Verbal Ability", "Technical")
SUBJECT_TIPS = {
    "Aptitude": "Work through the arithmetic in small steps, write down the formula, and check units before choosing an answer.",
    "Logical Reasoning": "Write the pattern or premises explicitly, then test each option against the information given.",
    "Verbal Ability": "Review the sentence rule or word meaning, then read the full sentence once for clarity.",
    "Technical": "Explain the core concept in your own words, then solve a small example before attempting a timed question.",
}


def _clean_text(value, field, minimum=8, maximum=500):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    text = re.sub(r"\s+", " ", value).strip()
    if not minimum <= len(text) <= maximum:
        raise ValueError(f"{field} has an invalid length")
    return text


def validate_analysis_response(payload, performances):
    if not isinstance(payload, dict):
        raise ValueError("Analysis must be a JSON object")
    subject_names = {item["subject"] for item in performances}
    raw_advice = payload.get("subject_advice")
    raw_roadmap = payload.get("roadmap")
    if not isinstance(raw_advice, list) or len(raw_advice) != len(subject_names):
        raise ValueError("Analysis must include advice for each assessed subject")
    advice_by_subject = {}
    for item in raw_advice:
        if not isinstance(item, dict) or item.get("subject") not in subject_names or item["subject"] in advice_by_subject:
            raise ValueError("Analysis contains an unknown or repeated subject")
        activities = item.get("activities")
        if not isinstance(activities, list) or not 1 <= len(activities) <= 5:
            raise ValueError("Each subject needs one to five practice activities")
        advice_by_subject[item["subject"]] = {
            "guidance": _clean_text(item.get("guidance"), "subject guidance"),
            "activities": [_clean_text(activity, "practice activity", 4, 180) for activity in activities],
        }
    if set(advice_by_subject) != subject_names:
        raise ValueError("Analysis is missing a subject")
    if not isinstance(raw_roadmap, list) or len(raw_roadmap) != 4:
        raise ValueError("Roadmap must contain four weeks")
    roadmap_by_week = {}
    for item in raw_roadmap:
        if not isinstance(item, dict) or isinstance(item.get("week"), bool) or not isinstance(item.get("week"), int) or item.get("week") not in range(1, 5):
            raise ValueError("Roadmap weeks must be numbered one to four")
        week = item["week"]
        if week in roadmap_by_week:
            raise ValueError("Roadmap has a repeated week")
        activities = item.get("activities")
        if not isinstance(activities, list) or not 1 <= len(activities) <= 4:
            raise ValueError("Each roadmap week needs one to four activities")
        roadmap_by_week[week] = {
            "week": week,
            "focus": _clean_text(item.get("focus"), "roadmap focus"),
            "activities": [_clean_text(activity, "roadmap activity", 4, 180) for activity in activities],
        }
    if set(roadmap_by_week) != {1, 2, 3, 4}:
        raise ValueError("Roadmap must include every week")

    normalized_performance = [
        {
            "subject": row["subject"],
            "correct_answers": int(row["correct_answers"]),
            "total_questions": int(row["total_questions"]),
            "score_percent": float(row["score_percent"]),
            "insight": row["insight"],
        }
        for row in performances
    ]
    strengths = [
        {"subject": row["subject"], **advice_by_subject[row["subject"]]}
        for row in normalized_performance if row["insight"] == "Strength"
    ]
    weaknesses = [
        {"subject": row["subject"], **advice_by_subject[row["subject"]]}
        for row in normalized_performance if row["insight"] == "Needs focus"
    ]
    priorities = sorted(normalized_performance, key=lambda item: (item["score_percent"], item["subject"]))[:3]
    return {
        "summary": _clean_text(payload.get("summary"), "analysis summary", 20, 1200),
        "actual_scores": normalized_performance,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "priorities": [
            {"rank": rank, "subject": row["subject"], "score_percent": row["score_percent"], **advice_by_subject[row["subject"]]}
            for rank, row in enumerate(priorities, start=1)
        ],
        "roadmap": [roadmap_by_week[week] for week in range(1, 5)],
    }


def fallback_analysis(performances, overall_score, correct, total):
    ordered = sorted(performances, key=lambda item: (item["score_percent"], item["subject"]))
    strengths = [
        {"subject": row["subject"], "guidance": "Maintain this result with mixed, timed practice.", "activities": ["Keep this subject in your weekly review.", "Explain one solved question aloud to check your reasoning."]}
        for row in performances if row["insight"] == "Strength"
    ]
    weaknesses = [
        {"subject": row["subject"], "guidance": SUBJECT_TIPS[row["subject"]], "activities": ["Review the concept behind missed questions.", "Complete a short untimed set, then check each solution."]}
        for row in performances if row["insight"] == "Needs focus"
    ]
    priorities = [
        {
            "rank": rank,
            "subject": row["subject"],
            "score_percent": row["score_percent"],
            "guidance": SUBJECT_TIPS[row["subject"]],
            "activities": ["Review the concepts behind missed questions.", "Practice a short set and explain each answer."],
        }
        for rank, row in enumerate(ordered[:3], start=1)
    ]
    focus_one = ordered[0]["subject"] if ordered else "all four subjects"
    focus_two = ordered[1]["subject"] if len(ordered) > 1 else focus_one
    return {
        "summary": f"Your assessment score was {overall_score:.1f}% ({correct} of {total} correct). Begin with {focus_one}, then review {focus_two}; these priorities come directly from your recorded subject results.",
        "actual_scores": performances,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "priorities": priorities,
        "roadmap": [
            {"week": 1, "focus": f"Revisit {focus_one} fundamentals", "activities": [f"Review the topics reflected in your {focus_one} result.", "Redo missed examples without a timer."]},
            {"week": 2, "focus": f"Build confidence in {focus_two}", "activities": [f"Study the key rules and methods for {focus_two}.", "Solve a short practice set and check each explanation."]},
            {"week": 3, "focus": "Practice across your priority subjects", "activities": [f"Complete mixed practice for {focus_one} and {focus_two}.", "Write down recurring mistakes and their corrections."]},
            {"week": 4, "focus": "Review and measure your progress", "activities": ["Take a timed mixed set.", "Compare the new subject results with this assessment."]},
        ],
    }


def validate_practice_question(payload, subject):
    if not isinstance(payload, dict):
        raise ValueError("Question must be a JSON object")
    if payload.get("subject") != subject:
        raise ValueError("Question subject does not match the request")
    options = payload.get("options")
    correct_option = payload.get("correct_option")
    if not isinstance(options, list) or len(options) != 4 or any(not isinstance(item, str) for item in options):
        raise ValueError("A question must have exactly four text options")
    options = [item.strip() for item in options]
    if any(not 1 <= len(item) <= 240 for item in options) or len({item.casefold() for item in options}) != 4:
        raise ValueError("Question options must be nonempty and distinct")
    if isinstance(correct_option, bool) or not isinstance(correct_option, int) or correct_option not in range(4):
        raise ValueError("The correct option must be an index from zero to three")
    return {
        "subject": subject,
        "prompt": _clean_text(payload.get("prompt"), "question prompt", 15, 600),
        "options": options,
        "correct_option": correct_option,
        "explanation": _clean_text(payload.get("explanation"), "answer explanation", 12, 1200),
    }


def fallback_chat_reply(message, profile, history):
    text = message.casefold()
    topics = {
        "Aptitude": ("percentage", "profit", "average", "speed", "ratio", "aptitude", "probability", "work problem"),
        "Logical Reasoning": ("logic", "reason", "sequence", "pattern", "syllogism", "direction"),
        "Verbal Ability": ("verbal", "grammar", "vocabulary", "sentence", "comprehension", "synonym"),
        "Technical": ("program", "python", "java", "coding", "dsa", "data structure", "algorithm", "complexity", "sql"),
        "Interview Preparation": ("interview", "resume", "behavioral", "hr round", "introduce yourself"),
    }
    topic = next((name for name, words in topics.items() if any(word in text for word in words)), "Placement Preparation")
    latest = history[0] if history else None
    subject_scores = latest["subjects"] if latest else []
    weakest = min(subject_scores, key=lambda row: row["score_percent"]) if subject_scores else None
    name = profile.get("name", "there")
    if weakest and topic == weakest["subject"]:
        personal_note = f" Your latest recorded score in {weakest['subject']} was {weakest['score_percent']:.1f}% ({weakest['correct_answers']} of {weakest['total_questions']}), so start with the concepts behind missed items."
    else:
        personal_note = ""
    tips = {
        "Aptitude": "Pick one formula, solve a worked example slowly, then do five similar questions without looking at the solution.",
        "Logical Reasoning": "List the given facts first. For a sequence, compare differences and ratios; for deductions, eliminate any option that adds an unstated fact.",
        "Verbal Ability": "Read the full sentence for context, identify the grammar or vocabulary rule, and then compare the choices.",
        "Technical": "State the core idea, trace it on a small input, and check time and space complexity before coding.",
        "Interview Preparation": "Use a brief situation, action, and result structure. Keep your example specific and connect it to the role.",
        "Placement Preparation": "Choose one topic, set a short practice goal, and review mistakes before moving on.",
    }
    return f"Hi {name}. I can’t reach Nemotron right now, but here’s a practical {topic.lower()} tip: {tips[topic]}{personal_note}"

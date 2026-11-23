SUBJECTS = ("Aptitude", "Logical Reasoning", "Verbal Ability", "Technical")

QUESTIONS = [
    {"subject": "Aptitude", "prompt": "A product costs ₹800. Its price increases by 25%. What is the new price?", "options": ["₹900", "₹1,000", "₹1,025", "₹1,200"], "correct_option": 1, "explanation": "25% of ₹800 is ₹200, so the new price is ₹1,000."},
    {"subject": "Aptitude", "prompt": "The average of 12, 18, 20, and 30 is:", "options": ["18", "19", "20", "21"], "correct_option": 2, "explanation": "The sum is 80. Dividing by 4 gives an average of 20."},
    {"subject": "Aptitude", "prompt": "A car travels 150 km in 3 hours. What is its average speed?", "options": ["45 km/h", "50 km/h", "55 km/h", "60 km/h"], "correct_option": 1, "explanation": "Average speed is distance divided by time: 150 ÷ 3 = 50 km/h."},
    {"subject": "Aptitude", "prompt": "A shirt marked at ₹2,000 is sold at a 10% discount. What is the selling price?", "options": ["₹1,700", "₹1,750", "₹1,800", "₹1,900"], "correct_option": 2, "explanation": "The discount is ₹200, so ₹2,000 − ₹200 = ₹1,800."},
    {"subject": "Aptitude", "prompt": "If 5 workers complete a job in 12 days, how many days would 10 workers take at the same rate?", "options": ["4", "5", "6", "8"], "correct_option": 2, "explanation": "The work is 5 × 12 = 60 worker-days. At 10 workers it takes 6 days."},
    {"subject": "Logical Reasoning", "prompt": "What comes next in the sequence 3, 7, 15, 31, …?", "options": ["47", "55", "62", "63"], "correct_option": 3, "explanation": "Each term is doubled and then increased by 1; 31 × 2 + 1 = 63."},
    {"subject": "Logical Reasoning", "prompt": "All analysts are graduates. Some graduates are designers. Which statement must be true?", "options": ["All designers are analysts", "Some analysts are designers", "All analysts are graduates", "No designers are graduates"], "correct_option": 2, "explanation": "The first statement directly establishes that all analysts are graduates."},
    {"subject": "Logical Reasoning", "prompt": "Mira faces north, turns right, then turns right again. Which direction is she facing?", "options": ["North", "East", "South", "West"], "correct_option": 2, "explanation": "Two right turns from north point south."},
    {"subject": "Logical Reasoning", "prompt": "Book is to reading as fork is to:", "options": ["Drawing", "Eating", "Writing", "Cooking"], "correct_option": 1, "explanation": "A book is used for reading; a fork is used for eating."},
    {"subject": "Logical Reasoning", "prompt": "If each letter is shifted forward by one, CAT becomes DBU. How is DOG written?", "options": ["EPH", "EPI", "FPH", "DPH"], "correct_option": 0, "explanation": "D→E, O→P, and G→H, giving EPH."},
    {"subject": "Verbal Ability", "prompt": "Choose the closest meaning of “concise”.", "options": ["Brief", "Unclear", "Careless", "Detailed"], "correct_option": 0, "explanation": "Concise means giving information clearly in few words."},
    {"subject": "Verbal Ability", "prompt": "Choose the grammatically correct sentence.", "options": ["She have completed the report.", "She has completed the report.", "She having completed the report.", "She are completing the report."], "correct_option": 1, "explanation": "“She” takes “has” in the present perfect tense."},
    {"subject": "Verbal Ability", "prompt": "Complete the sentence: Despite the heavy rain, the match continued ____.", "options": ["smooth", "smoothly", "smoothing", "smoothness"], "correct_option": 1, "explanation": "“Smoothly” is the adverb that describes how the match continued."},
    {"subject": "Verbal Ability", "prompt": "Choose the antonym of “reluctant”.", "options": ["Unwilling", "Hesitant", "Eager", "Unsure"], "correct_option": 2, "explanation": "Reluctant means unwilling; eager expresses the opposite."},
    {"subject": "Verbal Ability", "prompt": "Choose the correctly punctuated option.", "options": ["Before we begin lets review the agenda.", "Before we begin, let's review the agenda.", "Before, we begin let's review the agenda.", "Before we begin lets, review the agenda."], "correct_option": 1, "explanation": "The introductory phrase is followed by a comma, and “let's” needs an apostrophe."},
    {"subject": "Technical", "prompt": "Which data structure follows the LIFO principle?", "options": ["Queue", "Stack", "Linked list", "Graph"], "correct_option": 1, "explanation": "A stack removes the most recently added item first (last in, first out)."},
    {"subject": "Technical", "prompt": "What is the average time complexity of looking up a key in a hash table?", "options": ["O(1)", "O(log n)", "O(n)", "O(n log n)"], "correct_option": 0, "explanation": "A well-distributed hash table provides average constant-time lookup."},
    {"subject": "Technical", "prompt": "Which SQL clause filters rows before they are grouped?", "options": ["HAVING", "ORDER BY", "WHERE", "GROUP BY"], "correct_option": 2, "explanation": "WHERE filters individual rows before GROUP BY forms groups."},
    {"subject": "Technical", "prompt": "In object-oriented programming, which concept lets a class reuse behavior from another class?", "options": ["Encapsulation", "Inheritance", "Abstraction", "Overloading"], "correct_option": 1, "explanation": "Inheritance lets a subclass derive and reuse members from a parent class."},
    {"subject": "Technical", "prompt": "Which protocol is primarily used to securely browse websites?", "options": ["FTP", "HTTP", "HTTPS", "SMTP"], "correct_option": 2, "explanation": "HTTPS uses TLS to encrypt browser-to-server web traffic."},
]


def seed_question_bank(Question):
    from .extensions import db
    from .placement_bank import build_placement_questions

    legacy = []
    for question in QUESTIONS + EXTRA_QUESTIONS:
        category = {"Aptitude": "Aptitude", "Verbal Ability": "Communication", "Technical": "Technical"}.get(question["subject"], "Logical Reasoning")
        legacy.append({**question, "category": category, "source": "Original: Prepwise project",
                       "license": "Project original content; no third-party text reused",
                       "practice_only": question in EXTRA_QUESTIONS})
    bank = legacy + build_placement_questions()
    existing_rows = {row.prompt: row for row in Question.query.all()}
    existing = set(existing_rows)
    for question in bank:
        row = existing_rows.get(question["prompt"])
        if row:
            # Safe upgrade: tag legacy records once, while preserving authored Hub metadata.
            if row.category == "Legacy":
                row.category = question["category"]
                row.source = question["source"]
                row.license = question["license"]
            if row.topic == "General" and question.get("topic"):
                row.topic = question["topic"]
            continue
    additions = []
    for question in bank:
        if question["prompt"] in existing:
            continue
        payload = dict(question)
        payload.setdefault("practice_only", question in EXTRA_QUESTIONS)
        additions.append(Question(**payload))
    if additions:
        db.session.add_all(additions)
    if additions or existing_rows:
        db.session.commit()
EXTRA_QUESTIONS = [
    {"subject":"Aptitude","prompt":"A value rises from 80 to 100. What is the percentage increase?","options":["20%","25%","30%","35%"],"correct_option":1,"explanation":"The increase is 20; 20 divided by the original 80 is 25%."},
    {"subject":"Aptitude","prompt":"The average of five numbers is 14. If four numbers total 50, what is the fifth?","options":["18","20","22","24"],"correct_option":1,"explanation":"The total is 5 × 14 = 70; 70 − 50 = 20."},
    {"subject":"Aptitude","prompt":"A train covers 180 km in 2.5 hours. What is its average speed?","options":["60 km/h","68 km/h","72 km/h","75 km/h"],"correct_option":2,"explanation":"Speed is distance divided by time: 180 ÷ 2.5 = 72 km/h."},
    {"subject":"Aptitude","prompt":"An item marked at 1,500 is discounted by 20%. What is its sale price?","options":["1,100","1,200","1,250","1,300"],"correct_option":1,"explanation":"20% of 1,500 is 300; the sale price is 1,200."},
    {"subject":"Aptitude","prompt":"Twelve workers finish a job in 8 days. At the same rate, how long will 16 workers take?","options":["4 days","5 days","6 days","7 days"],"correct_option":2,"explanation":"The work is 12 × 8 = 96 worker-days; 96 ÷ 16 = 6 days."},
    {"subject":"Logical Reasoning","prompt":"Find the next number: 2, 6, 18, 54, __.","options":["108","144","162","216"],"correct_option":2,"explanation":"Each term is multiplied by 3, so 54 × 3 = 162."},
    {"subject":"Logical Reasoning","prompt":"All roses are flowers. No flowers are stones. Which must be true?","options":["Some stones are roses","No roses are stones","All stones are roses","Some flowers are stones"],"correct_option":1,"explanation":"Roses are flowers, and flowers are not stones; therefore roses are not stones."},
    {"subject":"Logical Reasoning","prompt":"A person faces east, turns left, then turns around. Which direction now?","options":["North","South","East","West"],"correct_option":1,"explanation":"Facing east, a left turn faces north; turning around faces south."},
    {"subject":"Logical Reasoning","prompt":"Thermometer is to temperature as compass is to:","options":["Speed","Direction","Distance","Time"],"correct_option":1,"explanation":"A thermometer measures temperature; a compass indicates direction."},
    {"subject":"Logical Reasoning","prompt":"If each letter moves back one place, FISH becomes EHRG. How does LAMP become?","options":["KZLO","KZMO","LBMQ","JZLO"],"correct_option":0,"explanation":"Move each letter back one: L→K, A→Z, M→L, P→O."},
    {"subject":"Verbal Ability","prompt":"Choose the closest meaning of 'abundant'.","options":["Scarce","Plentiful","Hidden","Fragile"],"correct_option":1,"explanation":"Abundant means existing in large quantities; plentiful is closest."},
    {"subject":"Verbal Ability","prompt":"Choose the correct sentence.","options":["They was waiting outside.","They were waiting outside.","They is waiting outside.","They be waiting outside."],"correct_option":1,"explanation":"The plural subject 'they' takes 'were' in the past progressive."},
    {"subject":"Verbal Ability","prompt":"Complete the sentence: The team worked ____ to meet the deadline.","options":["efficient","efficiency","efficiently","efficiencies"],"correct_option":2,"explanation":"The adverb 'efficiently' describes how the team worked."},
    {"subject":"Verbal Ability","prompt":"Choose the antonym of 'expand'.","options":["Enlarge","Extend","Contract","Increase"],"correct_option":2,"explanation":"Contract means to become smaller, the opposite of expand."},
    {"subject":"Verbal Ability","prompt":"Choose the correctly punctuated sentence.","options":["Its a useful tool, isnt it?","It's a useful tool, isn't it?","Its a useful tool isn't it.","It's a useful tool isnt it?"],"correct_option":1,"explanation":"Both contractions need apostrophes, and the question ends with a question mark."},
    {"subject":"Technical","prompt":"Which data structure is commonly used to implement breadth-first search?","options":["Stack","Queue","Heap","Tree"],"correct_option":1,"explanation":"A queue processes discovered nodes in first-in, first-out order for BFS."},
    {"subject":"Technical","prompt":"Binary search on a sorted array has what time complexity?","options":["O(1)","O(log n)","O(n)","O(n²)"],"correct_option":1,"explanation":"Each comparison halves the remaining search interval."},
    {"subject":"Technical","prompt":"Which SQL clause filters grouped results after aggregation?","options":["WHERE","HAVING","SELECT","LIMIT"],"correct_option":1,"explanation":"HAVING filters groups after GROUP BY and aggregate calculations."},
    {"subject":"Technical","prompt":"What does encapsulation primarily do in object-oriented programming?","options":["Combines data and methods while controlling access","Creates multiple parent classes","Runs code in parallel","Sorts object properties"],"correct_option":0,"explanation":"Encapsulation bundles state and behavior and controls access to internal details."},
    {"subject":"Technical","prompt":"Which HTTP status code indicates a successful creation?","options":["200","201","301","404"],"correct_option":1,"explanation":"HTTP 201 Created indicates that a request successfully created a resource."},
]

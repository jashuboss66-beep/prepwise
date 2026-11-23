"""Original Placement Learning Hub question corpus and structural validation."""
from math import comb, gcd

SOURCE = "Original: Prepwise Placement Learning Hub"
LICENSE = "Project original content; no third-party text reused"

APTITUDE_TOPICS = [
    "Percentages", "Profit and Loss", "Simple and Compound Interest", "Time and Work",
    "Time, Speed and Distance", "Averages", "Ratio and Proportion", "Probability",
    "Permutations and Combinations", "Number Systems", "HCF and LCM", "Problems on Ages",
    "Mixtures and Allegations", "Pipes and Cisterns", "Data Interpretation", "Simplification",
]
COMMUNICATION_TOPICS = [
    "Grammar", "Vocabulary", "Synonyms and Antonyms", "Sentence Correction", "Sentence Completion",
    "Error Identification", "Para Jumbles", "Reading Comprehension", "Verbal Reasoning",
    "Business Communication", "Professional Email Writing", "Workplace Communication", "Interview Communication",
]
TECHNICAL_TOPICS = [
    "C Programming", "C++", "Python", "Java", "Object-Oriented Programming", "Data Structures and Algorithms",
    "DBMS", "SQL", "Operating Systems", "Computer Networks", "Software Engineering", "Computer Fundamentals",
]


def _fmt(value):
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _choices(answer, step=1, suffix=""):
    answer = float(answer)
    values = [answer, answer + step, answer - step, answer + 2 * step]
    if min(values) < 0:
        values = [answer, answer + step, answer + 2 * step, answer + 3 * step]
    labels = [f"{_fmt(value)}{suffix}" for value in values]
    return labels, labels.index(f"{_fmt(answer)}{suffix}")


def _question(subject, category, topic, prompt, answer, distractors, explanation, difficulty, reference_url=None):
    options = [str(answer)] + [str(item) for item in distractors]
    if len(set(options)) != 4:
        raise ValueError(f"Question options are not distinct: {prompt}")
    # Rotate the original choices deterministically; assessments also shuffle per attempt.
    shift = sum(ord(char) for char in prompt) % 4
    options = options[shift:] + options[:shift]
    return {"subject": subject, "category": category, "topic": topic, "prompt": prompt,
            "options": options, "correct_option": options.index(str(answer)), "explanation": explanation,
            "difficulty": difficulty, "source": SOURCE, "license": LICENSE, "reference_url": reference_url,
            "practice_only": True}


def _aptitude_questions():
    rows = []
    for i in range(12):
        base = 100 + i * 25
        percent = 10 + (i % 7) * 5
        answer = base * (100 + percent) // 100
        opts, correct = _choices(answer, max(5, base // 20))
        rows.append(_question("Aptitude", "Aptitude", "Percentages",
            f"A training budget of {base} credits increases by {percent}%. What is the new budget?", opts[correct],
            [value for j, value in enumerate(opts) if j != correct], f"The increase is {base} × {percent}/100 = {base * percent // 100} credits, so the new budget is {_fmt(answer)} credits.",
            ("easy", "medium", "hard")[i % 3]))
        cost = 200 + i * 40
        rate = 10 + (i % 5) * 5
        sell = cost * (100 + rate) // 100
        opts, correct = _choices(sell, 10)
        rows.append(_question("Aptitude", "Aptitude", "Profit and Loss",
            f"A shop buys a device for {cost} units and applies a {rate}% markup. What is its selling price?", opts[correct],
            [value for j, value in enumerate(opts) if j != correct], f"Markup = {cost} × {rate}/100. Add that amount to the cost to get {_fmt(sell)} units.",
            ("easy", "medium", "hard")[(i + 1) % 3]))
        principal, annual_rate, years = 1000 + 500 * i, 4 + i % 6, 1 + i % 3
        interest = principal * annual_rate * years // 100
        total = principal + interest
        opts, correct = _choices(total, 50)
        rows.append(_question("Aptitude", "Aptitude", "Simple and Compound Interest",
            f"Find the amount on {principal} units at {annual_rate}% simple annual interest for {years} years.", opts[correct],
            [value for j, value in enumerate(opts) if j != correct], f"Simple interest is PRT/100 = {interest}; amount = principal + interest = {total} units.",
            ("easy", "medium", "hard")[i % 3]))
        first, second = 6 + i % 7, 8 + (i * 2) % 9
        combined = first * second / (first + second)
        answer_text = _fmt(combined)
        distractors = [_fmt(first + second), _fmt(abs(first - second)), _fmt(first * second / max(1, abs(first - second)))]
        if len(set([answer_text] + distractors)) < 4:
            distractors = [str(first + second), str(first), str(second)]
        rows.append(_question("Aptitude", "Aptitude", "Time and Work",
            f"Worker A finishes a task in {first} days and worker B in {second} days. How many days do they need together?", answer_text,
            distractors, f"Their combined daily rate is 1/{first} + 1/{second}; the time is {first} × {second}/({first} + {second}) = {answer_text} days.",
            ("easy", "medium", "hard")[(i + 1) % 3]))
        speed, hours = 36 + i * 4, 2 + i % 5
        distance = speed * hours
        opts, correct = _choices(distance, max(5, speed // 3))
        rows.append(_question("Aptitude", "Aptitude", "Time, Speed and Distance",
            f"A shuttle travels at {speed} km/h for {hours} hours. How far does it travel?", opts[correct],
            [value for j, value in enumerate(opts) if j != correct], f"Distance = speed × time = {speed} × {hours} = {distance} km.",
            ("easy", "medium", "hard")[(i + 2) % 3]))
        numbers = [10 + i, 14 + i * 2, 18 + i, 22 + i * 3]
        average = sum(numbers) // len(numbers)
        opts, correct = _choices(average, 2)
        rows.append(_question("Aptitude", "Aptitude", "Averages",
            f"A report lists {', '.join(map(str, numbers))} completed tasks over four days. What is the average per day?", opts[correct],
            [value for j, value in enumerate(opts) if j != correct], f"Add the four counts ({sum(numbers)}) and divide by 4 to get {average}.",
            ("easy", "medium", "hard")[i % 3]))
        parts_a, parts_b, total = 2 + i % 5, 3 + i % 4, (2 + i % 5 + 3 + i % 4) * (5 + i % 4)
        share = (2 + i % 5) * (5 + i % 4)
        opts, correct = _choices(share, 5)
        rows.append(_question("Aptitude", "Aptitude", "Ratio and Proportion",
            f"A fund of {total} units is divided in the ratio {parts_a}:{parts_b}. How many units go to the first share?", opts[correct],
            [value for j, value in enumerate(opts) if j != correct], f"The first share is {parts_a}/({parts_a}+{parts_b}) of {total}, which is {share} units.",
            ("easy", "medium", "hard")[(i + 1) % 3]))
        total_outcomes, favorable = 8 + i % 7, 2 + i % 4
        favorable = min(favorable, total_outcomes - 1)
        probability = f"{favorable}/{total_outcomes}"
        distractors = [f"{favorable + 1}/{total_outcomes}", f"{total_outcomes - favorable}/{total_outcomes}", f"1/{total_outcomes}"]
        if len(set([probability] + distractors)) < 4:
            distractors = [f"{favorable}/{total_outcomes - 1}", f"{total_outcomes - favorable}/{total_outcomes}", "1/2"]
        rows.append(_question("Aptitude", "Aptitude", "Probability",
            f"A box has {total_outcomes} equally likely tokens, of which {favorable} are marked. What is the probability of drawing a marked token?", probability,
            distractors, f"Probability = favorable outcomes / total outcomes = {favorable}/{total_outcomes}.", ("easy", "medium", "hard")[i % 3]))
        n, r = 5 + i % 5, 2 + i % 3
        r = min(r, n)
        value = comb(n, r)
        opts, correct = _choices(value, max(1, value // 5))
        rows.append(_question("Aptitude", "Aptitude", "Permutations and Combinations",
            f"A team of {r} reviewers is selected from {n} volunteers. How many different teams are possible?", opts[correct],
            [value for j, value in enumerate(opts) if j != correct], f"Order does not matter, so use combinations: {n}C{r} = {value}.", ("easy", "medium", "hard")[(i + 2) % 3]))
        dec, base_system = 20 + i * 7, 2 + i % 5
        digits, temp = "0123456789ABCDEF", dec
        converted = "0" if temp == 0 else ""
        while temp:
            converted = digits[temp % base_system] + converted
            temp //= base_system
        distractors = [str(dec), converted + "0", converted[:-1] or "1"]
        if len(set([converted] + distractors)) < 4:
            distractors = [str(dec + 1), str(dec - 1), converted + "1"]
        rows.append(_question("Aptitude", "Aptitude", "Number Systems",
            f"Write decimal {dec} in base {base_system}.", converted, distractors,
            f"Repeated division by {base_system} gives remainders that read in reverse order: {converted}.", ("easy", "medium", "hard")[i % 3]))
        a, b = 24 + i * 2, 36 + i * 3
        hcf = gcd(a, b); lcm = a * b // hcf
        value = hcf if i % 2 == 0 else lcm
        opts, correct = _choices(value, max(1, value // 6))
        label = "HCF" if i % 2 == 0 else "LCM"
        rows.append(_question("Aptitude", "Aptitude", "HCF and LCM",
            f"Find the {label} of {a} and {b}.", opts[correct], [item for j, item in enumerate(opts) if j != correct],
            f"The HCF is {hcf}; using HCF × LCM = {a} × {b}, the LCM is {lcm}.", ("easy", "medium", "hard")[i % 3]))
        child_age, gap, years = 8 + i % 9, 20 + i % 13, 3 + i % 5
        future = child_age + years
        parent_future = child_age + gap + years
        opts, correct = _choices(parent_future, 2)
        rows.append(_question("Aptitude", "Aptitude", "Problems on Ages",
            f"A parent is {gap} years older than a child aged {child_age}. What will be the parent's age in {years} years?", opts[correct],
            [value for j, value in enumerate(opts) if j != correct], f"The parent is now {child_age}+{gap}={child_age+gap}; after {years} years the age is {parent_future}.", ("easy", "medium", "hard")[(i + 1) % 3]))
        low, high, quantity = 10 + i % 8, 25 + i % 9, 2 + i % 4
        mean = (low + high) / 2
        opts, correct = _choices(mean, 2.5)
        rows.append(_question("Aptitude", "Aptitude", "Mixtures and Allegations",
            f"Equal quantities of solutions costing {low} and {high} units per litre are blended. What is the average cost per litre?", opts[correct],
            [value for j, value in enumerate(opts) if j != correct], f"For equal quantities, the mean cost is ({low}+{high})/2 = {_fmt(mean)} units per litre.", ("easy", "medium", "hard")[(i + 2) % 3]))
        fill, drain = 6 + i % 5, 15 + i % 7
        net = 1 / fill - 1 / drain
        hours_needed = 1 / net
        answer_text = _fmt(hours_needed)
        distractors = [_fmt(fill + drain), _fmt(drain - fill), _fmt(fill * drain / (drain - fill))]
        if len(set([answer_text] + distractors)) < 4:
            distractors = [_fmt(hours_needed + 3), _fmt(hours_needed + 5), _fmt(hours_needed + 7)]
        rows.append(_question("Aptitude", "Aptitude", "Pipes and Cisterns",
            f"An inlet fills a tank in {fill} hours while an outlet empties it in {drain} hours. How long to fill the empty tank if both are open?", answer_text,
            distractors, f"Net rate = 1/{fill} − 1/{drain}; reciprocal time = {answer_text} hours.", ("easy", "medium", "hard")[i % 3]))
        values = [20 + i * 2, 25 + i * 3, 18 + i * 4]
        rise = values[1] - values[0]
        opts, correct = _choices(rise, 2)
        rows.append(_question("Aptitude", "Aptitude", "Data Interpretation",
            f"A small chart records {values[0]} visits on Monday, {values[1]} on Tuesday, and {values[2]} on Wednesday. How many more visits were there Tuesday than Monday?", opts[correct],
            [value for j, value in enumerate(opts) if j != correct], f"Subtract Monday's {values[0]} from Tuesday's {values[1]} to get {rise} visits.", ("easy", "medium", "hard")[(i + 1) % 3]))
        x, y, z = 2 + i % 6, 3 + (i * 2) % 7, 4 + i % 5
        result = x + y * z
        opts, correct = _choices(result, 2)
        rows.append(_question("Aptitude", "Aptitude", "Simplification",
            f"Evaluate {x} + {y} × {z} using standard order of operations.", opts[correct],
            [value for j, value in enumerate(opts) if j != correct], f"Multiplication comes first: {y} × {z} = {y*z}; then add {x} to obtain {result}.", ("easy", "medium", "hard")[(i + 2) % 3]))
    return rows[:190]


def _communication_questions():
    rows = []
    data = {
        "Grammar": [
            ("Each of the interns ___ a weekly update.", "submits", ["submit", "are submit", "have submits"], "The singular subject each takes the singular verb submits."),
            ("By the time the call began, Mira ___ the slides.", "had prepared", ["prepares", "has prepare", "will preparing"], "The earlier completed action uses the past perfect."),
            ("Neither the manager nor the analysts ___ available today.", "are", ["is", "was", "be"], "With neither/nor, the verb agrees with the nearer plural subject analysts."),
            ("The report, together with its appendix, ___ ready.", "is", ["are", "were", "have"], "The main subject report is singular; the interrupting phrase does not change agreement."),
            ("Please send the form ___ Friday afternoon.", "by", ["at", "from", "during"], "By marks the latest acceptable deadline."),
            ("If I ___ the meeting notes, I would share them now.", "had", ["have", "will have", "am having"], "The unreal conditional uses a past-form verb in the if-clause."),
            ("The team has finished ___ review of the draft.", "its", ["their", "it's", "them"], "Team is treated as a single unit here; its is the possessive pronoun."),
            ("The candidate spoke ___ during the presentation.", "clearly", ["clear", "clarity", "clearest"], "An adverb modifies the verb spoke."),
            ("We look forward to ___ with your team.", "working", ["work", "worked", "works"], "The phrase look forward to is followed by a gerund."),
            ("The files ___ on the shared drive yesterday.", "were saved", ["saved", "are save", "have saving"], "The passive past form is were saved."),
            ("There are fewer errors in this version ___ in the first draft.", "than", ["then", "that", "as"], "Comparisons using fewer take than."),
            ("Could you tell me ___ the review starts?", "when", ["what", "which", "whose"], "When introduces a question about time."),
        ],
        "Vocabulary": [
            ("In a project brief, what does 'feasible' mean?", "Practical to carry out", ["Already completed", "Difficult to explain", "Unrelated to the goal"], "Feasible describes something that can reasonably be done."),
            ("A 'concise' update is:", "Brief but informative", ["Long and repetitive", "Unclear and indirect", "Missing its main point"], "Concise communication conveys the needed information in few words."),
            ("A 'tentative' schedule is:", "Subject to change", ["Guaranteed final", "Already overdue", "Unrelated to timing"], "Tentative means provisional rather than settled."),
            ("To 'mitigate' a risk is to:", "Reduce its impact", ["Ignore its existence", "Increase its likelihood", "Record it as complete"], "Mitigate means make less severe or harmful."),
            ("A 'transparent' process is:", "Open and easy to understand", ["Hidden from participants", "Based on guesswork", "Changed without notice"], "Transparency means information and decisions are visible."),
            ("An 'ambiguous' instruction is:", "Open to more than one meaning", ["Precisely measurable", "Already approved", "Written as a checklist"], "Ambiguous wording can be interpreted in multiple ways."),
            ("A 'reliable' source is one that is:", "Dependable and consistent", ["Always anonymous", "Recently edited", "Difficult to access"], "Reliable means trustworthy and consistent."),
            ("A 'priority' is something that:", "Deserves attention first", ["Can never be changed", "Has no deadline", "Is unrelated to a goal"], "A priority is treated as more important than other tasks."),
            ("To 'collaborate' means to:", "Work together toward a result", ["Avoid sharing updates", "Compete for the same role", "Delay a decision"], "Collaboration is joint work toward a shared outcome."),
            ("A 'precise' measurement is:", "Specific and accurate", ["Approximate and broad", "Unrecorded", "Unrelated to the task"], "Precise information is exact and clearly defined."),
            ("To 'allocate' resources is to:", "Assign them for particular uses", ["Remove every restriction", "Return them without review", "Combine all records"], "Allocate means distribute or assign for a purpose."),
            ("A 'constructive' comment is intended to:", "Help improve the work", ["Dismiss the person", "Hide the issue", "End the discussion"], "Constructive feedback points toward improvement."),
        ],
        "Synonyms and Antonyms": [
            ("Choose a synonym for 'adapt'.", "Adjust", ["Resist", "Forget", "Divide"], "Adapt means adjust to new conditions."),
            ("Choose an antonym for 'expand'.", "Contract", ["Enlarge", "Extend", "Increase"], "Contract means become smaller, the opposite of expand."),
            ("Choose a synonym for 'assist'.", "Help", ["Hinder", "Replace", "Inspect"], "Assist means help or support."),
            ("Choose an antonym for 'accurate'.", "Incorrect", ["Exact", "Reliable", "Careful"], "Incorrect is the opposite of accurate."),
            ("Choose a synonym for 'brief'.", "Concise", ["Lengthy", "Uncertain", "Complex"], "Concise means brief and to the point."),
            ("Choose an antonym for 'accept'.", "Reject", ["Receive", "Approve", "Admit"], "Reject means refuse, the opposite of accept."),
            ("Choose a synonym for 'improve'.", "Enhance", ["Damage", "Ignore", "Reduce"], "Enhance means improve or increase quality."),
            ("Choose an antonym for 'flexible'.", "Rigid", ["Adaptable", "Open", "Resilient"], "Rigid means not able to bend or change easily."),
            ("Choose a synonym for 'clarify'.", "Explain", ["Confuse", "Conceal", "Shorten"], "Clarify means make easier to understand."),
            ("Choose an antonym for 'include'.", "Exclude", ["Contain", "Involve", "Add"], "Exclude means leave out."),
            ("Choose a synonym for 'calm'.", "Composed", ["Agitated", "Urgent", "Noisy"], "Composed describes someone calm and controlled."),
        ],
        "Sentence Correction": [
            ("Choose the clearest sentence.", "Please review the draft before Thursday.", ["Please the draft review Thursday before.", "Thursday review before the draft please.", "Please review before draft the Thursday."], "A direct subject-verb-object order makes the request clear."),
            ("In a workplace update, choose the grammatically correct sentence.", "The results were shared with the project team.", ["The results was shared with the project team.", "The results has shared with the team.", "The results were share to the team."], "Plural results takes were; the passive participle is shared."),
            ("Choose the sentence with the correct comparison.", "This approach is more efficient than the earlier one.", ["This approach is most efficient than the earlier one.", "This approach is efficienter then the earlier one.", "This approach is more efficient from the earlier one."], "The comparative more efficient pairs with than."),
            ("Choose the sentence with consistent tense.", "She reviewed the request and sent a reply.", ["She reviews the request and sent a reply.", "She reviewed the request and sends a reply.", "She reviewing the request and sent a reply."], "Both completed actions use the past tense."),
            ("Choose the sentence with correct pronoun agreement.", "Every applicant should bring a copy of the resume.", ["Every applicant should bring their resumes copy.", "Every applicant should bring it copy.", "Every applicants should bring a copy of their resume."], "Applicant is singular and the sentence uses a consistent possessive form."),
            ("Choose the most concise version.", "We postponed the review because the data was incomplete.", ["Due to the fact that the data was not complete, we postponed the review.", "The review was postponed by us due to incomplete data information.", "We postponed because of the reason that data was incomplete."], "The first sentence states the cause directly without redundant wording."),
            ("Choose the sentence with correct punctuation.", "After the interview, the panel shared its notes.", ["After the interview the panel, shared its notes.", "After, the interview the panel shared its notes.", "After the interview; the panel, shared its notes."], "An introductory phrase is followed by a comma."),
            ("Choose the sentence that avoids a dangling modifier.", "After reviewing the figures, Noor updated the forecast.", ["After reviewing the figures, the forecast was updated by Noor.", "Reviewing the figures, the forecast changed by Noor.", "After the figures review, Noor's forecast updating."], "The person reviewing the figures is clearly Noor."),
            ("Choose the sentence with a parallel list.", "The role involves planning, testing, and documenting releases.", ["The role involves planning, tests, and to document releases.", "The role involves to plan, testing, and documentation of releases.", "The role involves planning, to test, and releases are documented."], "The three list items use parallel -ing forms."),
            ("For a weekly status note, choose the correct sentence.", "There are fewer open tickets this week.", ["There is fewer open tickets this week.", "There are less open tickets this week.", "There were fewest open tickets this week than."], "Plural tickets takes are; fewer is used with countable items."),
            ("Choose the best revision.", "The team completed the prototype on schedule.", ["The prototype the team completed it on schedule.", "On schedule completed the team prototype.", "The team were completed the prototype schedule."], "The subject, verb, and object appear in a clear order."),
        ],
        "Sentence Completion": [
            ("The team documented each change so that future reviewers could ___.", "trace the decision", ["avoid the record", "repeat the error", "remove the context"], "Documentation helps later reviewers follow how a decision was made."),
            ("Although the initial estimate was uncertain, the revised forecast became ___.", "more precise", ["less related", "more accidental", "fully unrelated"], "A revised forecast that uses more evidence can become more precise."),
            ("The speaker paused to ___ the main recommendation before taking questions.", "summarize", ["conceal", "contradict", "postpone"], "A summary restates the key point before discussion."),
            ("The group agreed to test a small change first, rather than ___ the whole process.", "redesign", ["measure", "document", "review"], "Testing a small change avoids immediately redesigning everything."),
            ("Please include a clear subject line so the message is easy to ___.", "locate later", ["misplace now", "ignore entirely", "separate from its topic"], "A descriptive subject helps people find the message again."),
            ("A useful handover explains both the current status and the ___ next action.", "recommended", ["unrelated", "unrecorded", "contradictory"], "A handover should state the next action that follows from the current status."),
            ("When two deadlines conflict, the project lead should ___ which task has priority.", "confirm", ["hide", "erase", "guess at"], "Confirming priorities avoids assumptions about conflicting deadlines."),
            ("The instructions were rewritten in plain language to make them more ___.", "accessible", ["ambiguous", "technical", "lengthy"], "Plain language improves accessibility and understanding."),
            ("Before sending the proposal, check that each claim is supported by ___.", "evidence", ["decoration", "speculation", "repetition"], "Evidence supports factual claims in a proposal."),
            ("The interviewer asked a follow-up question to ___ the candidate's example.", "understand", ["interrupt", "hide", "replace"], "A follow-up question can clarify or deepen understanding of an example."),
            ("The meeting ended with each owner repeating their ___ and deadline.", "action item", ["disagreement", "introduction", "background"], "Repeating action items and deadlines confirms responsibilities."),
        ],
        "Error Identification": [
            ("Identify the error: 'The list of required documents are attached.'", "are", ["The", "list", "attached"], "The subject is singular list, so the verb should be is."),
            ("Identify the error: 'She explained me the new process.'", "explained me", ["She", "the new process", "new"], "Use explained the process to me, or told me about the process."),
            ("Identify the error: 'We discussed about the launch plan.'", "discussed about", ["We", "the launch plan", "launch"], "Discuss takes a direct object; remove about."),
            ("Identify the error: 'Please revert back by Monday.'", "revert back", ["Please", "by Monday", "Monday"], "Revert already means return; in business English, use reply by Monday."),
            ("Identify the error: 'The feedbacks were helpful.'", "feedbacks", ["The", "were", "helpful"], "Feedback is usually an uncountable noun; say the feedback was helpful."),
            ("Identify the error: 'I am looking forward to meet you.'", "to meet", ["I am", "looking forward", "you"], "Look forward to is followed by a noun or gerund: meeting."),
            ("Identify the error: 'He did not knew the schedule had changed.'", "knew", ["He", "did not", "had changed"], "After did not, use the base verb know."),
            ("Identify the error: 'Please find the report attach.'", "attach", ["Please find", "the report", "Please"], "The past participle attached describes the report."),
            ("Identify the error: 'The two teams has agreed.'", "has", ["The two teams", "agreed", "two"], "Plural teams takes have."),
            ("Identify the error: 'We have received your email yesterday.'", "have received", ["We", "your email", "yesterday"], "A finished past time such as yesterday takes simple past: received."),
            ("Identify the error: 'Kindly do the needful at the earliest.'", "do the needful", ["Kindly", "at the earliest", "the"], "Specific professional wording such as please complete the requested update is clearer."),
        ],
        "Para Jumbles": [
            ("Arrange the ideas: A) We reviewed the results. B) Then we chose one change. C) First, we collected feedback. D) Finally, we planned a follow-up test.", "C-A-B-D", ["A-C-D-B", "B-D-C-A", "D-B-A-C"], "The sequence moves from collecting feedback to reviewing it, choosing a change, then testing."),
            ("Arrange the email steps: A) State the request. B) Add a useful subject. C) Close with thanks. D) Give the necessary context.", "B-D-A-C", ["A-C-B-D", "D-B-C-A", "C-A-D-B"], "A clear email starts with a subject, gives context, states the request, and closes politely."),
            ("Arrange the interview process: A) Ask a follow-up. B) Listen to the example. C) Invite the candidate to answer. D) Summarize the key point.", "C-B-A-D", ["B-C-D-A", "D-A-C-B", "A-D-B-C"], "Invite an answer, listen, clarify with a follow-up, then summarize."),
            ("Arrange the report workflow: A) Check the figures. B) Share the final version. C) Draft the summary. D) Confirm the audience.", "D-A-C-B", ["C-B-D-A", "A-D-B-C", "B-C-A-D"], "Confirm the audience, verify the figures, draft for them, then share the final report."),
            ("Arrange the project handover: A) Name the next owner. B) List open issues. C) Record current status. D) Confirm the next deadline.", "C-B-A-D", ["A-D-C-B", "B-A-D-C", "D-C-A-B"], "A handover begins with status and open issues, then assigns an owner and deadline."),
            ("Arrange the presentation: A) Explain the recommendation. B) Introduce the purpose. C) Show the supporting evidence. D) Invite questions.", "B-C-A-D", ["A-D-B-C", "C-B-D-A", "D-A-C-B"], "Introduce the purpose, present evidence, give the recommendation, and invite questions."),
            ("Arrange the review loop: A) Apply the agreed revision. B) Gather comments. C) Share a draft. D) Confirm the final version.", "C-B-A-D", ["B-C-D-A", "A-D-B-C", "D-A-C-B"], "Share a draft, collect comments, revise, and confirm the final version."),
            ("Arrange a customer response: A) Offer a next step. B) Acknowledge the concern. C) Check the relevant facts. D) Explain the response.", "B-C-D-A", ["C-A-B-D", "D-B-A-C", "A-D-C-B"], "A helpful response acknowledges the issue, checks facts, explains, and offers a next step."),
            ("Arrange an incident update: A) Describe impact. B) State what is known. C) Give the next update time. D) Identify current action.", "B-A-D-C", ["A-D-C-B", "D-C-B-A", "C-B-A-D"], "Start with known facts, explain impact and action, then state when the next update will arrive."),
            ("Arrange an application: A) Thank the reader. B) Connect experience to the role. C) Name the role. D) Request a discussion.", "C-B-D-A", ["B-C-A-D", "D-A-C-B", "A-D-B-C"], "Name the role, connect relevant experience, request a discussion, and close politely."),
        ],
        "Reading Comprehension": [
            ("A team piloted a shorter daily stand-up for two weeks. The meeting became faster, but unresolved issues moved to a shared tracker. What changed?", "Routine updates were shortened and issues were tracked separately.", ["The team stopped recording blockers.", "The pilot removed every team meeting.", "The tracker replaced all project planning."], "The passage says the stand-up was shorter and unresolved issues went to a tracker."),
            ("A support group tagged requests by topic before assigning them. After a month, it found repeated questions and wrote a shared answer guide. What prompted the guide?", "Repeated questions appeared in the tagged requests.", ["The group stopped assigning requests.", "The guide was required before tagging.", "The month had no customer requests."], "The repeated questions discovered through topic tags motivated the guide."),
            ("A candidate practiced examples aloud and asked a peer to flag unclear explanations. The candidate then shortened two answers. Which skill was being improved?", "Clear and concise spoken communication", ["Typing speed", "Database normalization", "Meeting attendance"], "Speaking aloud and shortening unclear answers improves oral clarity."),
            ("A report showed a rise in sign-ups but did not include the number of visitors. The analyst added that denominator before comparing campaigns. Why?", "To interpret the sign-up rate in context", ["To remove all campaign data", "To make the report longer", "To avoid comparing rates"], "A denominator is needed to understand a rate."),
            ("A project team sent a draft early and invited comments. It incorporated feedback before approval. What was the benefit?", "Issues could be found before final approval.", ["Approval became unnecessary.", "The team avoided documenting changes.", "The draft could not be revised."], "Early review gives participants time to identify issues before final approval."),
            ("A manager moved a deadline after learning that a required dataset would arrive late. The team recorded the change and the reason. What practice does this show?", "Transparent expectation management", ["Silent scope expansion", "Avoiding accountability", "Unverified data analysis"], "The deadline change and its reason were shared and recorded."),
            ("A help page listed one task per numbered step and included screenshots only where a choice was unclear. What was the design goal?", "Make the instructions easy to follow", ["Increase jargon", "Hide decision points", "Replace the task with a quiz"], "Sequential steps and targeted images support usability."),
            ("Two employees disagreed about a proposal. They compared the evidence and agreed to test the smallest reversible change. What guided the decision?", "Evidence and a low-risk experiment", ["Seniority alone", "Avoiding measurement", "Choosing the largest change"], "They compared evidence and selected a reversible test."),
            ("An interviewer asks the same core question to each candidate and records evidence against shared criteria. What does this support?", "Consistent evaluation", ["Unstructured scoring", "Guaranteed identical answers", "Avoiding candidate questions"], "Common questions and criteria make evaluation more consistent."),
            ("A team posts a short status update with completed work, blockers, and the next step. What information does it make visible?", "Progress and immediate risks", ["Private personal details", "Only historical budgets", "Unrelated company policies"], "The update directly covers completed work, blockers, and next action."),
        ],
        "Verbal Reasoning": [
            ("All approved requests have an owner. Request R is approved. What follows?", "Request R has an owner.", ["Request R has no owner.", "Every request is approved.", "Only owners can submit requests."], "The rule applies to every approved request, including R."),
            ("If a report is late, the review meeting moves. The report is not late. What can be concluded?", "The rule alone does not determine whether the meeting moves.", ["The meeting must move.", "The report is incomplete.", "The meeting must be cancelled."], "The conditional states what happens if the report is late; it does not provide the converse."),
            ("A is scheduled before B. C is scheduled after B. Which order is guaranteed?", "A before B before C", ["C before A before B", "B before C before A", "A after C before B"], "Combining the two relations gives A < B < C."),
            ("Every urgent ticket is reviewed today. Ticket K is urgent. What must happen?", "Ticket K is reviewed today.", ["Ticket K is closed today.", "Every reviewed ticket is urgent.", "Ticket K is assigned to a manager."], "K meets the condition of being urgent, so the stated rule applies."),
            ("A team has exactly one presenter: Lee or Sam. Lee is not presenting. Who presents?", "Sam", ["Both Lee and Sam", "Neither person", "The audience"], "With exactly one of two choices and Lee excluded, Sam presents."),
            ("A task can start only after its requirements are approved. The requirements are not approved. What follows?", "The task cannot start yet.", ["The task is already complete.", "The task has been cancelled.", "The requirements are approved."], "Approval is a prerequisite; without it, the task cannot start."),
            ("Some reviewers are developers. All developers can read the test report. Which statement follows?", "Some reviewers can read the test report.", ["All reviewers are developers.", "No reviewers can read the report.", "All readers are reviewers."], "The reviewers who are developers inherit the stated ability."),
            ("A, B, and C each present once. A presents before C, and B presents after C. Who presents first?", "A", ["B", "C", "It cannot be determined"], "The order constraints give A before C before B."),
            ("If a build passes, a release candidate is created. A release candidate was not created. Assuming the rule is followed, what follows?", "The build did not pass.", ["The build passed.", "The release was deployed.", "The build was never started."], "By contrapositive, no candidate means the build did not pass."),
            ("Only staff with access can open the archive. Priya opened it. What follows?", "Priya has access.", ["Everyone has access.", "Priya created the archive.", "The archive is public."], "Access is necessary to open the archive, so Priya has it."),
        ],
        "Business Communication": [
            ("A client reports a missed delivery. What is the best first response?", "Acknowledge the issue and confirm you are checking the delivery status.", ["Blame another team immediately.", "Promise a new time without checking.", "Ignore the message until the next meeting."], "Acknowledge the concern and verify facts before committing to a resolution."),
            ("A meeting invite has no agenda. What is the most useful clarification?", "Ask what decision or outcome the meeting should reach.", ["Decline every future meeting.", "Send unrelated background files.", "Assume the meeting is cancelled."], "Clarifying the intended outcome helps participants prepare."),
            ("A colleague asks for an update you cannot verify yet. What should you say?", "State what is known and when you will confirm the rest.", ["Invent a likely answer.", "Avoid replying indefinitely.", "Present a guess as confirmed."], "Separate known facts from pending verification and set a follow-up time."),
            ("Which approach is best when disagreeing in a business review?", "Describe the evidence and invite discussion of alternatives.", ["Criticize the speaker personally.", "Interrupt until the proposal is withdrawn.", "Withhold the concern until after approval."], "Focus on evidence and options rather than personal criticism."),
            ("A decision affects two teams. What should the summary include?", "The decision, rationale, owners, and next steps.", ["Only the meeting start time.", "Unverified personal opinions.", "A list of unrelated messages."], "A decision record needs enough context for both teams to act."),
            ("A stakeholder asks for a status report. Which format is easiest to scan?", "Completed work, current risks, and next milestone.", ["A long unstructured chat transcript.", "Only the project title.", "An unexplained list of file names."], "A short structure makes progress, risks, and next steps clear."),
            ("A request is outside the agreed scope. What is the professional response?", "Explain the scope and propose a path to assess the request.", ["Reject the requester personally.", "Promise immediate delivery without review.", "Silently change the scope."], "Clarify the agreement and offer a transparent way to evaluate the change."),
            ("What should you do when a meeting runs beyond its planned time?", "Confirm whether attendees can continue or schedule the remaining items.", ["Keep everyone without checking.", "End without noting unfinished decisions.", "Add unrelated topics."], "Check availability and preserve outstanding agenda items."),
            ("A technical term may be unfamiliar to a client. What helps most?", "Use plain language and define the term briefly.", ["Add more unexplained acronyms.", "Avoid answering the question.", "Assume the client already knows it."], "Plain language supports a shared understanding."),
            ("A colleague gives useful feedback. What is an appropriate reply?", "Thank them and explain how you will consider the suggestion.", ["Dismiss it without reading.", "Forward it without context.", "Promise to use every suggestion automatically."], "Acknowledge feedback and respond thoughtfully without making an unsupported promise."),
        ],
        "Professional Email Writing": [
            ("Which subject line is most useful for a request to review a draft by Friday?", "Review requested: project draft by Friday", ["Hello", "Important!!!", "A few things"], "The subject states the action and deadline."),
            ("You need to move a meeting. What should the email include?", "The current time, proposed alternatives, and reason if relevant.", ["Only an apology.", "A new time with no notice.", "A request unrelated to the meeting."], "Recipients need enough detail to choose a replacement time."),
            ("Which opening is appropriate for a formal message to a known hiring manager?", "Dear Ms. Rao,", ["Hey!!!", "To whom it may concern, pal", "Yo there"], "A named, respectful greeting fits a professional email."),
            ("Which closing best fits a concise request for information?", "Thank you for your time; I look forward to your guidance.", ["Answer now.", "Whatever happens happens.", "No closing is needed in every case."], "A courteous closing matches a professional request."),
            ("You attach a requested portfolio. What should the message do?", "Mention the attachment and its contents.", ["Refer to an attachment that is not included.", "Leave the message body blank.", "Use a misleading file name."], "Mentioning the attachment helps the reader identify it."),
            ("Which sentence makes a clear action request?", "Could you approve the revised schedule by 3 p.m. Thursday?", ["The schedule is around.", "Approval maybe at some point.", "Thursday has several hours."], "The request states an action and a specific deadline."),
            ("You must correct information sent earlier. What is best?", "Send a prompt correction and identify the revised information.", ["Delete the message without notice.", "Repeat the error in a new subject.", "Wait until someone notices."], "A direct correction prevents continued use of wrong information."),
            ("Which practice protects recipients on a broad announcement?", "Use BCC when recipients do not need one another's addresses.", ["Put every address in the subject.", "Forward a private thread to everyone.", "Attach a password in the same public message."], "BCC avoids sharing addresses unnecessarily."),
            ("A message needs a reply from one person and awareness from another. Which fields fit?", "To for the action owner and CC for the person kept informed.", ["BCC for every recipient by default.", "Put both names only in the subject.", "Use Reply All without checking."], "To identifies the primary recipient; CC keeps another person informed."),
            ("Which message is clearest when you cannot meet the requested deadline?", "Explain the constraint and propose a realistic alternative date.", ["Promise the original date despite knowing it is impossible.", "Say nothing until the deadline passes.", "Send an empty email."], "Clear expectations and an alternative support coordination."),
        ],
        "Workplace Communication": [
            ("A teammate is blocked by an unclear requirement. What should you do?", "Ask a focused question and document the agreed interpretation.", ["Guess silently and continue.", "Blame the teammate in a group channel.", "Remove the requirement from the project."], "Clarification and a shared record prevent conflicting assumptions."),
            ("You notice a mistake in a shared report. What is the best action?", "Correct it transparently and notify affected readers if needed.", ["Hide the revision history.", "Delete the whole report without notice.", "Leave a known error for others."], "Transparent correction helps people use the accurate version."),
            ("A remote colleague has not seen a time-sensitive update. What helps?", "Use the agreed channel and include the deadline and requested action.", ["Send repeated messages on every platform.", "Assume silence means approval.", "Remove the deadline from the message."], "A concise update in the agreed channel is actionable."),
            ("How should a facilitator handle a discussion where one person dominates?", "Invite input from others and restate the decision question.", ["End the meeting without a summary.", "Allow only the loudest voice to decide.", "Change to an unrelated topic."], "Balanced participation keeps the discussion focused and inclusive."),
            ("You receive critical feedback. What is a constructive response?", "Ask for an example and identify a practical next step.", ["Argue about the person's motives.", "Ignore all future feedback.", "Accept every claim without clarification."], "Examples and next steps make feedback actionable."),
            ("Two teams use different names for the same status. What will reduce confusion?", "Agree on shared definitions and record them.", ["Add more status names.", "Avoid discussing the issue.", "Let each report redefine it."], "Shared definitions allow consistent interpretation."),
            ("What belongs in a useful handover note?", "Current status, open risks, owner, and next action.", ["Only informal impressions.", "A password written in plain text.", "Unrelated personal details."], "A handover should enable the next person to continue safely."),
            ("A teammate raises a concern during a review. What shows active listening?", "Paraphrase the concern and check that you understood it.", ["Prepare a rebuttal without listening.", "Change the subject immediately.", "Repeat only the last word."], "Paraphrasing and checking understanding confirms the message."),
            ("A shared channel becomes noisy. What is a helpful team agreement?", "Move detailed discussion to a thread and keep channel updates concise.", ["Stop sharing project status.", "Send every update to everyone privately.", "Disable all questions."], "Threads keep detail organized while preserving useful shared updates."),
            ("You cannot finish an assigned task on time. What should you do?", "Tell the owner early, explain the blocker, and agree on a recovery plan.", ["Wait until after the deadline.", "Mark the task done without evidence.", "Delete the task."], "Early notice lets the team adjust scope or timing."),
        ],
        "Interview Communication": [
            ("When asked about a challenge, which answer structure is useful?", "Describe the situation, your action, and the result.", ["Give an unrelated opinion.", "Describe only the team's name.", "Avoid explaining your contribution."], "A situation-action-result structure gives a focused example."),
            ("You do not know an interview answer. What is a strong response?", "Explain what you know, state the uncertainty, and describe how you would investigate.", ["Invent a confident answer.", "Criticize the question.", "Stop communicating."], "Honesty and a problem-solving approach show sound judgment."),
            ("What is appropriate when an interviewer asks if you have questions?", "Ask a relevant question about the role or team's work.", ["Ask for confidential employee data.", "Say the role has no responsibilities.", "Repeat a question already answered."], "A relevant question shows preparation and helps clarify expectations."),
            ("How should you describe a project contribution?", "State your specific responsibility and the outcome you observed.", ["Claim sole credit for all team work.", "List tools without explaining their use.", "Avoid naming your actions."], "Specific ownership and observed outcomes make a contribution clear."),
            ("An interviewer interrupts to ask for clarification. What should you do?", "Pause and answer the specific clarification directly.", ["Continue the memorized answer unchanged.", "Treat the question as criticism.", "End the interview."], "Responding directly shows listening and keeps the answer relevant."),
            ("How can you explain a technical concept to a nontechnical interviewer?", "Use a simple analogy and connect it to the user's problem.", ["Use unexplained acronyms.", "Avoid describing the concept.", "Assume the interviewer built the system."], "A simple analogy and user context make technical ideas accessible."),
            ("What should a candidate do after a virtual interview begins with audio trouble?", "Politely mention the issue and confirm when communication is clear.", ["Continue without being heard.", "Blame the interviewer.", "Leave without explanation."], "A concise check resolves the issue professionally."),
            ("How should you respond to a question about a mistake?", "Explain the lesson and the change you made afterward.", ["Say mistakes never happen.", "Blame another person only.", "Share unrelated confidential information."], "Reflection and corrective action make the example useful."),
            ("What is a professional way to close an interview?", "Thank the interviewer and confirm the next-step process if appropriate.", ["Demand an immediate decision.", "Leave without a closing.", "Ask for another candidate's score."], "A courteous close supports clear expectations."),
            ("Your answer is becoming too long. What helps?", "State the key point first and give one relevant example.", ["Add more unrelated details.", "Repeat the question several times.", "Switch to a different topic."], "A main point plus one example keeps the answer focused."),
        ],
    }
    for topic, items in data.items():
        for i, (prompt, answer, distractors, explanation) in enumerate(items):
            rows.append(_question("Verbal Ability", "Communication", topic, prompt, answer, distractors,
                                  explanation, ("easy", "medium", "hard")[i % 3]))
    # Add original short situational variants across communication topics to reach the target pool.
    situations = [
        ("Business Communication", "A project decision changes after new evidence arrives. What should the update do?", "State what changed and why.", ["Hide the earlier decision.", "Blame the first reviewer.", "Remove the evidence."], "A transparent update records the new decision and its evidence."),
        ("Professional Email Writing", "Which opening best suits an email requesting a short review?", "Could you review the attached draft by Tuesday?", ["Read this now!!!", "I am writing for a reason maybe.", "No request is included."], "A direct request includes the action and a clear deadline."),
        ("Workplace Communication", "A task has two possible owners. What should the team do?", "Confirm one accountable owner and record the assignment.", ["Assume both will do it.", "Leave ownership blank.", "Assign it to an absent person without notice."], "One explicit owner prevents the task from being missed."),
        ("Interview Communication", "You are asked why you want the role. What is most relevant?", "Connect your skills and interests to the role's described work.", ["Give a memorized answer unrelated to the role.", "Ask the interviewer to answer for you.", "Discuss confidential details from another employer."], "A relevant answer connects your motivation and skills to the role."),
        ("Verbal Reasoning", "Every reviewed item has a reference number. Item Q was reviewed. What follows?", "Item Q has a reference number.", ["Every item was reviewed.", "Q is unresolved.", "Only Q has a reference number."], "The general rule applies to reviewed item Q."),
        ("Reading Comprehension", "A team tested two layouts with users and chose the one that reduced missed steps. What informed the choice?", "Observed user results", ["A random preference", "The longest layout", "An unrelated budget"], "The team selected the layout based on observed missed-step results."),
        ("Grammar", "Choose the correct phrase: 'The information ___ available to all reviewers.'", "is", ["are", "were be", "have"], "Information is an uncountable singular noun in this sentence."),
        ("Vocabulary", "In a review, 'verify' means to:", "Check that something is accurate", ["Make it less visible", "Replace it without checking", "Delay it indefinitely"], "Verify means confirm accuracy with evidence."),
        ("Sentence Correction", "Choose the clearest update.", "The team will publish the revised guide tomorrow.", ["Tomorrow revised the guide team publish will.", "The team tomorrow revised guide publish.", "The revised tomorrow guide is team publish."], "The sentence has a clear subject, action, object, and time."),
        ("Sentence Completion", "To avoid conflicting versions, the editor named one file as the ___.", "source of truth", ["untracked draft", "unrelated attachment", "temporary guess"], "A source of truth identifies the authoritative version."),
    ]
    for i in range(20):
        topic, prompt, answer, distractors, explanation = situations[i % len(situations)]
        prompt = prompt.replace("tomorrow", ("tomorrow", "the next day", "the agreed date", "the following morning")[i // len(situations)]) if "tomorrow" in prompt and i // len(situations) < 4 else prompt
        rows.append(_question("Verbal Ability", "Communication", topic, f"{prompt} (practice scenario {i + 1})", answer,
                              distractors, explanation, ("easy", "medium", "hard")[i % 3]))
    return rows[:140]


def _technical_questions():
    # Each compact concept record yields two differently framed, original checks.
    facts = {
        "C Programming": [
            ("array indexes begin at zero", "zero-based indexing", ["one-based indexing", "hash indexing", "reverse indexing"], "A program accesses the first array element at index 0."),
            ("a pointer stores the address of an object", "pointer", ["loop", "macro", "label"], "A function needs to pass an object's location to another function."),
            ("printf writes formatted output to standard output", "printf", ["scanf", "malloc", "fopen"], "A program needs to display a formatted status line."),
            ("malloc requests a block of dynamic memory", "malloc", ["free", "strlen", "return"], "The program needs memory whose size is decided while it runs."),
            ("free releases dynamically allocated memory", "free", ["printf", "sizeof", "continue"], "A dynamically allocated block is no longer needed."),
            ("a C string ends with the null character", "null terminator", ["newline only", "space character", "semicolon"], "A character array stores text that library string functions can recognize."),
            ("sizeof reports the storage size of a type or object", "sizeof", ["strlen", "strcmp", "fscanf"], "A program needs the byte size occupied by a variable."),
            ("a struct groups named fields that may have different types", "structure", ["union only", "preprocessor macro", "loop counter"], "A record needs a name, an identifier, and a numeric score."),
            ("a function declaration gives a function's interface before use", "function prototype", ["array initializer", "pointer arithmetic", "case label"], "A source file calls a function defined later."),
            ("the address-of operator obtains an object's address", "& operator", ["* operator only", "% operator", "! operator"], "A program needs to pass a variable by its address."),
        ],
        "C++": [
            ("a constructor initializes a newly created object", "constructor", ["destructor", "namespace", "iterator"], "A class needs to establish valid member values when an object is created."),
            ("a destructor runs when an object's lifetime ends", "destructor", ["constructor", "template", "overload"], "An object must release a resource at the end of its lifetime."),
            ("a reference is an alias for an existing object", "reference", ["header", "namespace", "literal"], "A function should use another name for an existing integer variable."),
            ("a virtual function supports dynamic dispatch through a base pointer", "virtual function", ["static variable", "friend declaration", "macro"], "A base-class pointer should call the derived override at runtime."),
            ("std::vector is a resizable sequence container", "vector", ["tuple", "queue adapter only", "bit field"], "A program needs an indexed collection that can grow."),
            ("a template lets code work with types supplied as parameters", "template", ["namespace", "destructor", "linker flag"], "One algorithm should support several element types."),
            ("RAII ties resource ownership to object lifetime", "RAII", ["manual global cleanup", "preprocessor condition", "multiple inheritance"], "A file handle should close automatically when its owning scope ends."),
            ("function overloading uses one name with different parameter lists", "overloading", ["overriding", "encapsulation", "namespacing"], "Two functions share a name but accept different argument types."),
            ("a namespace groups names and helps avoid collisions", "namespace", ["constructor", "reference", "loop"], "Two libraries define similarly named helper functions."),
            ("const marks an object or method as not modifying the relevant value", "const", ["volatile only", "mutable only", "virtual"], "A method promises not to change the object's observable state."),
        ],
        "Python": [
            ("dictionary keys are unique within one dictionary", "dictionary", ["list", "tuple", "string"], "A lookup needs to map each username to one profile."),
            ("a tuple is an immutable sequence", "tuple", ["list", "set", "dictionary"], "A fixed coordinate pair should not be modified after creation."),
            ("list.append adds one item to the end of a list", "append", ["extend only", "sort", "pop"], "A program needs to add one result to a list."),
            ("range's stop value is excluded", "range", ["slice assignment", "enumerate", "zip"], "A loop uses range(2, 5) and needs to know its final value."),
            ("def begins a function definition", "def", ["class", "yield", "lambda only"], "A module needs to declare a named reusable function."),
            ("indentation defines a suite of statements", "indentation", ["semicolon count", "brace nesting", "line length"], "Python must determine which statements belong to an if block."),
            ("except handles a matching exception raised in a try block", "except", ["finally only", "assert", "with"], "A program needs to recover from a file-not-found error."),
            ("a set stores unique hashable elements", "set", ["list", "tuple", "string"], "A program needs distinct tags and fast membership checks."),
            ("enumerate yields an index together with each iterable item", "enumerate", ["range only", "reversed", "sorted"], "A loop needs both a position and a value from a list."),
            ("a context manager can manage setup and cleanup around a block", "with statement", ["global statement", "pass statement", "match statement"], "A file should be closed automatically after its block runs."),
        ],
        "Java": [
            ("the JVM executes Java bytecode", "Java Virtual Machine", ["Java compiler only", "garbage collector only", "package manager"], "Compiled class files need a runtime to execute."),
            ("an interface declares a contract that implementing classes provide", "interface", ["constructor", "package", "primitive"], "Several unrelated classes should expose the same operation."),
            ("garbage collection reclaims unreachable heap objects", "garbage collector", ["compiler", "class loader only", "thread scheduler"], "An application no longer references some allocated objects."),
            ("static members belong to the class rather than each instance", "static", ["private", "abstract", "synchronized"], "A counter should be shared across all objects of a class."),
            ("a constructor has the class name and no return type", "constructor", ["method overload only", "package declaration", "interface field"], "A new object needs initialization during creation."),
            ("array length is available through the length field", "length", ["size()", "count()", "capacity()"], "Code needs the number of elements in a Java array."),
            ("checked exceptions must be caught or declared", "checked exception", ["unchecked warning", "runtime annotation", "generic bound"], "A method calls an API that declares an IOException."),
            ("a package organizes related classes and helps name them", "package", ["thread", "constructor", "literal"], "A project groups classes under a shared namespace."),
            ("generics provide compile-time type parameters for reusable classes", "generics", ["reflection only", "serialization", "synchronization"], "A collection should enforce the element type at compile time."),
            ("String objects are immutable", "String", ["StringBuilder", "array", "StringBuffer only"], "A method appends text without changing the original String object."),
        ],
        "Object-Oriented Programming": [
            ("encapsulation groups state with operations and controls access", "encapsulation", ["recursion", "linking", "normalization"], "A class should protect its fields behind methods."),
            ("inheritance derives a new type from an existing type", "inheritance", ["composition only", "overloading", "serialization"], "A specialized type reuses and extends a base type."),
            ("polymorphism lets one interface refer to objects with different implementations", "polymorphism", ["compilation", "tokenization", "indexing"], "The same call should dispatch to different object behavior."),
            ("abstraction exposes essential behavior while hiding implementation detail", "abstraction", ["duplication", "global state", "casting"], "A caller needs to use a service without knowing its internal steps."),
            ("composition builds an object from collaborating component objects", "composition", ["inheritance", "overloading", "parsing"], "A report object contains a formatter and a data source."),
            ("method overriding supplies a derived implementation of an inherited method", "overriding", ["overloading", "shadowing only", "templating"], "A subclass changes the implementation of a base operation."),
            ("a class describes the structure and behavior of its instances", "class", ["instance", "method call", "package"], "A design defines fields and methods for many objects."),
            ("an object is a particular instance of a class", "object", ["interface", "constructor declaration", "module"], "A program creates one customer record from a customer type."),
            ("a private member restricts direct access to its declaring class", "private access", ["public access", "global access", "dynamic dispatch"], "Internal state should not be read directly by unrelated classes."),
            ("a constructor establishes an object's initial valid state", "constructor", ["destructor", "interface", "operator"], "A new account object needs a starting balance and identifier."),
        ],
        "Data Structures and Algorithms": [
            ("a stack removes the most recently added item first", "stack", ["queue", "heap only", "graph"], "Undo operations need last-in-first-out behavior."),
            ("a queue removes items in first-in-first-out order", "queue", ["stack", "tree", "hash map"], "Requests should be processed in arrival order."),
            ("binary search repeatedly halves a sorted search range", "binary search", ["linear search", "depth-first search", "bubble sort"], "A sorted array needs an efficient lookup by value."),
            ("a hash table maps keys to values using a hash function", "hash table", ["stack", "linked list only", "trie only"], "A program needs average constant-time key lookup."),
            ("a linked list stores elements connected through references", "linked list", ["array", "heap", "matrix"], "A sequence needs nodes connected by next references."),
            ("breadth-first search explores neighbors level by level", "breadth-first search", ["depth-first search", "binary search", "insertion sort"], "An unweighted graph needs shortest path by number of edges."),
            ("depth-first search explores a path before backtracking", "depth-first search", ["breadth-first search", "counting sort", "hashing"], "A traversal should follow a branch deeply before trying another."),
            ("merge sort divides data, sorts parts, and merges them", "merge sort", ["selection sort", "linear search", "heap lookup"], "A stable divide-and-conquer sorting method is needed."),
            ("a binary search tree orders smaller keys left and larger keys right", "binary search tree", ["queue", "stack", "hash set"], "A tree should support ordered key lookup under its ordering rule."),
            ("Big-O describes an asymptotic growth upper bound", "Big-O notation", ["unit test", "hash key", "pointer"], "An engineer compares how runtime scales as input grows."),
        ],
        "DBMS": [
            ("a primary key uniquely identifies each row", "primary key", ["foreign key", "view", "index hint"], "A table needs a unique identifier for every record."),
            ("a foreign key refers to a key in another table", "foreign key", ["candidate key only", "trigger", "cursor"], "An order row must refer to an existing customer."),
            ("normalization reduces certain forms of data redundancy", "normalization", ["denormalization", "sharding", "back up"], "A schema repeats customer details on many order rows."),
            ("a transaction groups database operations into a logical unit", "transaction", ["index", "view", "schema"], "Several updates must succeed or fail together."),
            ("atomicity means a transaction is all-or-nothing", "atomicity", ["isolation", "durability", "consistency"], "A transfer must not debit without crediting."),
            ("consistency preserves database rules across a transaction", "consistency", ["atomicity", "availability", "caching"], "Constraints must remain satisfied after a committed change."),
            ("isolation controls interactions among concurrent transactions", "isolation", ["durability", "normalization", "projection"], "Concurrent work should not observe prohibited intermediate state."),
            ("durability means committed data survives a failure", "durability", ["atomicity", "cardinality", "selectivity"], "A committed update must remain after a restart."),
            ("an index can speed reads but adds storage and write overhead", "index", ["trigger", "cursor", "view"], "A frequently filtered column needs faster lookup."),
            ("a view presents a saved query as a virtual table", "view", ["transaction", "primary key", "log file"], "Users need a reusable read-only projection of joined data."),
        ],
        "SQL": [
            ("WHERE filters rows before grouping", "WHERE", ["HAVING", "ORDER BY", "GROUP BY"], "A query should remove inactive rows before aggregation."),
            ("HAVING filters groups after aggregation", "HAVING", ["WHERE", "FROM", "JOIN"], "A query should keep only groups with a count above a threshold."),
            ("GROUP BY forms groups for aggregate calculations", "GROUP BY", ["ORDER BY", "LIMIT", "DISTINCT"], "A report needs total orders for each customer."),
            ("ORDER BY sorts the returned rows", "ORDER BY", ["GROUP BY", "WHERE", "INSERT"], "A result should display newest records first."),
            ("INNER JOIN returns rows with matching values in both inputs", "INNER JOIN", ["LEFT JOIN", "CROSS JOIN", "UNION"], "A report should include only orders with a matching customer."),
            ("LEFT JOIN keeps every row from the left input", "LEFT JOIN", ["INNER JOIN", "RIGHT EXCLUDE", "INTERSECT"], "A report must include customers even if they have no orders."),
            ("COUNT counts rows or non-null values depending on its argument", "COUNT", ["SUM", "AVG", "COALESCE"], "A query needs the number of matching records."),
            ("COMMIT makes the current transaction's changes permanent", "COMMIT", ["ROLLBACK", "DROP", "EXPLAIN"], "A validated update should be saved."),
            ("ROLLBACK discards uncommitted transaction changes", "ROLLBACK", ["COMMIT", "GRANT", "ALTER"], "A failed operation should undo its pending changes."),
            ("a parameterized query separates values from SQL syntax", "parameterized query", ["string concatenation", "cartesian join", "stored result"], "User input must be supplied safely to a database query."),
        ],
        "Operating Systems": [
            ("a process is a running program with its execution state", "process", ["source file", "compiler flag", "database row"], "An operating system schedules an executing application."),
            ("a thread is an execution path within a process", "thread", ["file system", "device driver only", "page table"], "One process performs multiple concurrent tasks."),
            ("virtual memory gives processes an abstraction of address space", "virtual memory", ["cache line", "register file", "shell script"], "A program should use addresses independent of physical RAM placement."),
            ("a deadlock involves processes waiting indefinitely for resources", "deadlock", ["context switch", "cache miss", "compilation"], "Two tasks each hold a resource needed by the other."),
            ("a scheduler selects which ready task runs next", "scheduler", ["linker", "parser", "formatter"], "The operating system needs to choose a process for CPU time."),
            ("a system call requests a service from the operating system", "system call", ["user macro", "database join", "network packet"], "An application needs the OS to open a file."),
            ("a page fault occurs when an accessed page is not currently mapped in memory", "page fault", ["syntax error", "deadlock", "interrupt vector"], "An address references a page that must be loaded or mapped."),
            ("a mutex provides mutual exclusion for a critical section", "mutex", ["queue", "compiler", "socket"], "Only one thread at a time should update a shared structure."),
            ("context switching saves one execution state and restores another", "context switch", ["memory leak", "linking", "normalization"], "The CPU moves from running one task to another."),
            ("a file system organizes and locates stored files", "file system", ["scheduler", "interpreter", "register"], "Users need named files arranged in directories."),
        ],
        "Computer Networks": [
            ("DNS maps domain names to network records such as IP addresses", "DNS", ["DHCP", "HTTP", "SMTP"], "A browser needs to resolve a host name before connecting."),
            ("TCP provides a reliable, ordered byte stream", "TCP", ["UDP", "ARP", "ICMP only"], "An application needs delivery order and retransmission."),
            ("UDP sends datagrams without built-in delivery guarantees", "UDP", ["TCP", "TLS", "DNS"], "A real-time service prefers low overhead and can handle some loss."),
            ("HTTPS protects HTTP communication with TLS", "HTTPS", ["FTP", "SMTP", "Telnet"], "A browser needs an encrypted web connection."),
            ("an IP address identifies a network interface for routing", "IP address", ["MAC vendor name", "port label", "URL path"], "Routers need an address to forward packets."),
            ("a router forwards packets between networks", "router", ["compiler", "switch port only", "database index"], "Traffic must move from a local network toward another network."),
            ("a switch forwards frames within a local network using link-layer addresses", "network switch", ["router", "DNS resolver", "load test"], "Devices on one LAN need local frame delivery."),
            ("TLS helps authenticate peers and encrypt data in transit", "TLS", ["DNS", "DHCP", "HTML"], "A client needs a protected session with a server."),
            ("a subnet mask separates network and host portions of an address", "subnet mask", ["port number", "URL fragment", "checksum only"], "An interface needs to determine whether a destination is local."),
            ("a port number identifies an application endpoint on a host", "port number", ["MAC address", "subnet mask", "domain suffix"], "A host sends traffic to a particular service process."),
        ],
        "Software Engineering": [
            ("a unit test checks a small piece of behavior in isolation", "unit test", ["load test", "release note", "deployment"], "A developer verifies one function's expected result."),
            ("integration testing checks interactions between components", "integration test", ["unit test only", "code formatting", "licence scan"], "A service and database must work together correctly."),
            ("version control records and coordinates changes to files", "version control", ["compiler", "cache", "proxy"], "Several developers need history and collaboration on source changes."),
            ("continuous integration runs automated checks on proposed changes", "continuous integration", ["manual deployment only", "data normalization", "encryption key"], "A team wants tests to run whenever code is submitted."),
            ("code review examines a change before it is merged", "code review", ["load balancing", "runtime compilation", "index scan"], "A teammate checks a proposed change for clarity and defects."),
            ("requirements describe needed behavior or constraints", "requirements", ["compiled binary", "cache line", "commit hash"], "A team must agree what the system should do."),
            ("refactoring improves internal structure without intended behavior change", "refactoring", ["feature expansion", "data deletion", "deployment rollback"], "A developer simplifies duplicated logic while preserving behavior."),
            ("a regression test checks that a fixed defect does not return", "regression test", ["smoke alarm", "style guide", "prototype"], "A previously failing case should remain correct after later changes."),
            ("an API contract describes how software components communicate", "API contract", ["database backup", "layout grid", "memory page"], "A client needs the request and response format expected by a service."),
            ("a release rollback restores a previous usable version", "rollback", ["refactoring", "normalization", "encryption"], "A production release causes an incident and the prior version is safe."),
        ],
        "Computer Fundamentals": [
            ("binary uses two digit symbols, 0 and 1", "binary", ["decimal", "hexadecimal only", "octal only"], "A digital representation uses two states for each digit."),
            ("RAM is volatile working memory", "RAM", ["ROM only", "SSD", "optical disk"], "Working data is lost when power is removed."),
            ("an SSD stores data in solid-state flash memory", "SSD", ["CPU register", "network switch", "printer buffer"], "A computer needs persistent storage with no spinning disk."),
            ("the CPU executes instructions and coordinates operations", "CPU", ["monitor", "keyboard", "power supply only"], "A computer component fetches and executes program instructions."),
            ("a bit is a binary digit", "bit", ["byte", "word", "packet"], "A value represents one of two states."),
            ("a byte commonly contains eight bits", "byte", ["nibble", "kilobyte always", "pixel"], "A storage unit contains eight binary digits."),
            ("firmware is software stored to control hardware behavior", "firmware", ["spreadsheet", "temporary cache", "network cable"], "A device needs persistent low-level control instructions."),
            ("an operating system manages hardware and provides services to programs", "operating system", ["text editor", "database table", "router port"], "Applications need common services for memory, files, and devices."),
            ("a compiler translates source code into another form such as machine code", "compiler", ["router", "database view", "monitor"], "A program's source must be translated before native execution."),
            ("a cache stores copies of data for faster later access", "cache", ["archive", "firewall rule", "source file"], "Frequently used data should be available with lower access latency."),
        ],
    }
    rows = []
    for topic, records in facts.items():
        for index, (description, answer, distractors, scenario) in enumerate(records):
            variants = [
                (f"Which concept best matches this description: {description}?", f"The description identifies {answer}: {description}.",
                 ("easy", "medium", "hard")[index % 3]),
                (f"A developer faces this situation: {scenario} Which concept is the best fit?", f"{answer} is the relevant concept because {description}.",
                 ("medium", "hard", "easy")[(index + 1) % 3]),
            ]
            for prompt, explanation, difficulty in variants:
                rows.append(_question("Technical", "Technical", topic, prompt, answer, distractors, explanation, difficulty))
    return rows


def build_placement_questions():
    questions = _aptitude_questions() + _communication_questions() + _technical_questions()
    expected = {"Aptitude": 190, "Communication": 140, "Technical": 240}
    counts = {category: sum(item["category"] == category for item in questions) for category in expected}
    if counts != expected:
        raise ValueError(f"Placement bank target counts mismatch: {counts}")
    validate_question_list(questions)
    return questions


def validate_question_list(questions):
    seen = set()
    for index, item in enumerate(questions, start=1):
        required = {"subject", "category", "topic", "prompt", "options", "correct_option", "explanation", "difficulty", "source", "license"}
        if not required.issubset(item):
            raise ValueError(f"Question {index} is missing fields: {required - set(item)}")
        if item["prompt"] in seen:
            raise ValueError(f"Duplicate question prompt at item {index}")
        seen.add(item["prompt"])
        if len(item["options"]) != 4 or len({option.casefold() for option in item["options"]}) != 4:
            raise ValueError(f"Question {index} must have four distinct answer options")
        if not isinstance(item["correct_option"], int) or item["correct_option"] not in range(4):
            raise ValueError(f"Question {index} has an invalid answer key")
        if item["difficulty"] not in {"easy", "medium", "hard"}:
            raise ValueError(f"Question {index} has an invalid difficulty")
        if not item["explanation"].strip() or not item["source"].strip() or not item["license"].strip():
            raise ValueError(f"Question {index} is missing explanation or provenance")
    return {"count": len(questions), "unique_prompts": len(seen), "validated": len(seen)}

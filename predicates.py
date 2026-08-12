"""
Dataset-specific predicate (crisp) query functions.
Each classify_* function returns a dict per record with:
    passes   : bool   -> predicate result (True = satisfies query conditions)
    category : str    -> justified relationship label (for the report)
    tier     : str    -> relevance tier fed into the fuzzy layer
"""
from ebook_ai_system import keyword_match_strength, AI_KEYWORDS, \
    PROGRAMMING_KEYWORDS, MATH_KEYWORDS, CYBER_KEYWORDS

# ---------------------------------------------------------------------------
# Dataset B discipline vocabularies (derived from inspecting the catalogue)
# ---------------------------------------------------------------------------
B_AI_DISC = {"Artificial Intelligence"}
B_PROG_DISC_L3 = {
    "Introduction to Programming", "CS0 / Pre-Programming",
    "Object Oriented Programming", "Data Structures", "Software Engineering",
    "Web Programming and Design", "Computer Organization",
    "Programming Languages", "Compilers", "Intermediate / Advanced Programming",
}
B_PROG_DISC_L4 = {
    "Java", "Python", "C", "C++", "C#", "Visual Basic", "Programming Logic",
    "Data Structures", "Web Programming", "Web Design", "Software Engineering",
    "Object Oriented Programming", "Object Oriented Design",
    "Computer Organization", "Other Languages", "Android Programming",
    "Compilers", "Programming Languages",
}
B_MATH_L2 = {"Calculus, Applied & Advanced Math", "Statistics", "Precalculus"}
B_MATH_L3 = {"Advanced Math", "Statistics"}
B_CYBER_DISC = {"Computer Security"}


# =====================  SCENARIO 1  =========================================

def classify_A_scenario1(row):
    title = row["Title"]
    dept = row.get("Recommended by", "")
    ai_hit = keyword_match_strength(title, AI_KEYWORDS)
    prog_hit = keyword_match_strength(title, PROGRAMMING_KEYWORDS)
    math_hit = keyword_match_strength(title, MATH_KEYWORDS)
    dept_cs = (dept == "CS/IT")

    if ai_hit:
        return dict(passes=True, category="Directly AI-related", tier="direct")
    if prog_hit:
        tier = "strong" if dept_cs else "support"
        return dict(passes=True, category="Programming support", tier=tier)
    if math_hit:
        return dict(passes=True, category="Mathematical support", tier="support")
    return dict(passes=False, category="Not relevant", tier="none")


def classify_B_scenario1(row):
    l1, l2, l3, l4 = row["Discipline (Level 1)"], row["Discipline (Level 2)"], \
        row["Discipline (Level 3)"], row["Discipline (Level 4)"]
    if l3 in B_AI_DISC or l4 in B_AI_DISC:
        return dict(passes=True, category="Directly AI-related", tier="direct")
    if l3 in B_PROG_DISC_L3 or l4 in B_PROG_DISC_L4:
        tier = "strong" if l1 == "Engineering and Computer Science" else "support"
        return dict(passes=True, category="Programming support", tier=tier)
    if l1 == "Mathematics" and (l2 in B_MATH_L2 or l3 in B_MATH_L3):
        return dict(passes=True, category="Mathematical support", tier="support")
    return dict(passes=False, category="Not relevant", tier="none")


def classify_C_scenario1(row):
    title, category, discipline = row["Title"], row["Category"], row["Discipline"]
    discipline = discipline.strip() if isinstance(discipline, str) else discipline
    ai_hit = keyword_match_strength(title, AI_KEYWORDS)
    prog_hit = keyword_match_strength(title, PROGRAMMING_KEYWORDS)

    if ai_hit:
        return dict(passes=True, category="Directly AI-related", tier="direct")
    if category == "Computing" and discipline in (
        "IT, Programming, Web Development", "Computing: Intro Computing", "Computing"
    ) and prog_hit:
        tier = "strong" if discipline == "IT, Programming, Web Development" else "support"
        return dict(passes=True, category="Programming support", tier=tier)
    if category == "Mathematics and Statistics":
        return dict(passes=True, category="Mathematical support", tier="support")
    return dict(passes=False, category="Not relevant", tier="none")


# =====================  SCENARIO 2  =========================================

def classify_A_scenario2(row):
    title = row["Title"]
    dept = row.get("Recommended by", "")
    cyber_hit = keyword_match_strength(title, CYBER_KEYWORDS)
    if cyber_hit:
        tier = "direct" if dept == "CS/IT" else "strong"
        return dict(passes=True, category="Cybersecurity-related", tier=tier)
    return dict(passes=False, category="Not relevant", tier="none")


def classify_B_scenario2(row):
    l3, l4, title = row["Discipline (Level 3)"], row["Discipline (Level 4)"], row["Title"]
    if l3 in B_CYBER_DISC or l4 in B_CYBER_DISC:
        return dict(passes=True, category="Directly security-related", tier="direct")
    if keyword_match_strength(title, CYBER_KEYWORDS):
        return dict(passes=True, category="Related (title match only)", tier="weak")
    return dict(passes=False, category="Not relevant", tier="none")


def classify_C_scenario2(row):
    title, category, discipline = row["Title"], row["Category"], row["Discipline"]
    discipline = discipline.strip() if isinstance(discipline, str) else discipline
    cyber_hit = keyword_match_strength(title, CYBER_KEYWORDS)
    if cyber_hit and category == "Computing":
        tier = "direct" if discipline == "IT, Programming, Web Development" else "strong"
        return dict(passes=True, category="Directly security-related", tier=tier)
    if cyber_hit:
        return dict(passes=True, category="Related (title match only)", tier="weak")
    return dict(passes=False, category="Not relevant", tier="none")

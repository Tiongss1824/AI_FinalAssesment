"""
BTIS3043 AI Final Assessment
Predicate + Fuzzy eBook Query System
=====================================
Loads three eBook catalogues (Dataset A - Existing Collection, Dataset B -
Academic Catalogue, Dataset C - Acquisition/Licensing Catalogue), runs
predicate (crisp/Boolean) queries for two fixed scenarios, then layers a
fuzzy-logic suitability evaluation on top of the predicate results and
produces ranked, explainable output.

Design notes (see report for full justification):
- Predicate layer answers: "does this record satisfy the query conditions?"
  Implemented as plain Python/pandas boolean functions (crisp set membership).
- Fuzzy layer answers: "how suitable is this record, in degrees [0,1]?"
  Implemented with hand-rolled triangular/trapezoidal membership functions
  (no external fuzzy library required) combined with a weighted-average
  aggregation ("simple additive weighting"), which is a standard, explainable
  fuzzy-rule aggregation approach for multi-criteria ranking.
"""

import re
import numpy as np
import pandas as pd
from datetime import datetime

CURRENT_YEAR = 2026  # assessment year, used for recency fuzzification

# ---------------------------------------------------------------------------
# 1. DATA LOADING
# ---------------------------------------------------------------------------

def load_datasets(path_a, path_b, path_c):
    a = pd.read_excel(path_a)
    b = pd.read_excel(path_b)
    c = pd.read_excel(path_c)
    return a, b, c


# ---------------------------------------------------------------------------
# 2. KEYWORD DICTIONARIES (used for title-text predicates where no discipline
#    field exists, e.g. Dataset A, and as a secondary check on B & C)
# ---------------------------------------------------------------------------

AI_KEYWORDS = [
    "artificial intelligence", "intelligent system", "machine learning",
    "computer vision", "robotic", "expert system", "knowledge representation",
    "neural network", "deep learning", " ai ", "ai,", "ai:"
]

PROGRAMMING_KEYWORDS = [
    "python", "java", "c++", "javascript", "programming", "algorithm",
    "data structure", "software engineering", "object oriented",
    "web development", "web programming", "coding", " c#", "visual basic",
    "software design"
]

MATH_KEYWORDS = [
    "calculus", "statistics", "probability", "linear algebra",
    "discrete math", "mathematic", "optimization", "decision analysis",
    "applied math", "precalculus", "quantitative"
]

CYBER_KEYWORDS = [
    "cybersecurity", "cyber security", "computer security", "network security",
    "cryptography", "cryptology", "digital forensic", "information assurance",
    "secure system", "secure computing", "information security",
    "penetration testing", "ethical hacking", "incident response",
    "security awareness", "security fundamentals", "security analyst",
    "corporate computer security", "security in computing", "security",
]

# Generic terms (e.g. "security") can false-positive on unrelated domains
# (food security, national security, job security). Exclude those explicitly
# so a bare "security" hit only counts when it is not one of these contexts.
CYBER_FALSE_POSITIVE_CONTEXTS = [
    "food security", "job security", "social security", "national security",
    "border security", "energy security", "homeland security",
    "income security", "retirement security",
]


def _text_hits(text, keyword_list):
    """Return number of distinct keywords found in text (lower-cased)."""
    if not isinstance(text, str):
        return 0
    t = " " + text.lower() + " "
    hits = 0
    for kw in keyword_list:
        if kw not in t:
            continue
        if kw == "security" and keyword_list is CYBER_KEYWORDS:
            # bare "security" must not be part of a known unrelated phrase
            if any(fp in t for fp in CYBER_FALSE_POSITIVE_CONTEXTS):
                continue
        hits += 1
    return hits


def keyword_match_strength(text, keyword_list):
    """Crisp predicate helper: True/False whether ANY keyword is present."""
    return _text_hits(text, keyword_list) > 0


# ---------------------------------------------------------------------------
# 3. FUZZY MEMBERSHIP FUNCTIONS
# ---------------------------------------------------------------------------

def trapmf(x, a, b, c, d):
    """Standard trapezoidal membership function on scalar or array x."""
    x = np.asarray(x, dtype=float)
    y = np.zeros_like(x)
    # rising edge
    if b > a:
        idx = (x >= a) & (x < b)
        y[idx] = (x[idx] - a) / (b - a)
    # plateau
    idx = (x >= b) & (x <= c)
    y[idx] = 1.0
    # falling edge
    if d > c:
        idx = (x > c) & (x <= d)
        y[idx] = (d - x[idx]) / (d - c)
    return y


def fuzzy_recency(copyright_year, current_year=CURRENT_YEAR):
    """
    Membership in fuzzy set RECENT, based on book age in years.
    0-3 years old  -> fully recent (1.0)
    3-7 years old  -> linearly decreasing ("relatively recent")
    >7 years old   -> not recent (0.0)
    Age computed per-record; function handles scalars.
    """
    if pd.isna(copyright_year):
        return 0.3  # unknown -> mild default, neither penalised nor rewarded
    age = current_year - float(copyright_year)
    age = max(age, 0)
    val = trapmf(np.array([age]), -1, 0, 3, 7)[0]
    return float(val)


def fuzzy_affordability(price, low, high):
    """
    Membership in fuzzy set AFFORDABLE, normalised against the min/max price
    observed among the CANDIDATE (predicate-passing) records of that dataset
    for that scenario, so affordability is judged relative to comparable
    options rather than an arbitrary fixed currency threshold.
    price <= low  -> 1.0 (cheapest tier, fully affordable)
    price >= high -> 0.0 (most expensive tier, not affordable)
    linear between.
    """
    if pd.isna(price) or high <= low:
        return 0.5  # no price info / no spread -> neutral membership
    val = trapmf(np.array([price]), low, low, low, high)[0]
    return float(val)


def fuzzy_format_suitability(fmt):
    """
    Membership in fuzzy set FORMAT-SUITABLE.
    ePub / PDF are readable on virtually any device without extra software
    -> high suitability. Adobe-Reader-locked files need a specific reader
    -> moderate suitability. Unknown -> neutral.
    This is a simple fuzzy singleton assignment (a justified expert rule),
    not a continuous membership function, since eBook format is categorical.
    """
    if not isinstance(fmt, str):
        return 0.5
    f = fmt.strip().lower()
    if f in ("epub", "pdf"):
        return 1.0
    if "adobe" in f:
        return 0.6
    return 0.5


def fuzzy_relevance_from_tier(tier):
    """
    Membership in fuzzy set TOPIC-RELEVANT, derived from a discrete
    relevance tier assigned during the predicate stage (see classify_*
    functions below). Tiers are mapped to membership degrees:
      'direct'   -> 1.00  (exact discipline / strong multi-keyword match)
      'strong'   -> 0.80
      'support'  -> 0.55  (programming/math support, or single keyword hit)
      'weak'     -> 0.30
      'none'     -> 0.00
    """
    mapping = {"direct": 1.0, "strong": 0.8, "support": 0.55,
               "weak": 0.30, "none": 0.0}
    return mapping.get(tier, 0.0)


def weighted_fuzzy_score(memberships, weights):
    """Simple additive weighting (SAW) aggregation of fuzzy memberships."""
    memberships = np.asarray(memberships, dtype=float)
    weights = np.asarray(weights, dtype=float)
    weights = weights / weights.sum()
    return float(np.dot(memberships, weights))


# ---------------------------------------------------------------------------
# 4. GENERIC RESULT FORMATTER
# ---------------------------------------------------------------------------

def add_rank(df, score_col="fuzzy_score", ascending=False):
    out = df.sort_values(score_col, ascending=ascending).reset_index(drop=True)
    out.insert(0, "Rank", range(1, len(out) + 1))
    return out

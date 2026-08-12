import pandas as pd
import numpy as np
from ebook_ai_system import (
    load_datasets, fuzzy_recency, fuzzy_affordability, fuzzy_format_suitability,
    fuzzy_relevance_from_tier, weighted_fuzzy_score, add_rank
)
from predicates import (
    classify_A_scenario1, classify_B_scenario1, classify_C_scenario1,
    classify_A_scenario2, classify_B_scenario2, classify_C_scenario2,
)

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

A, B, C = load_datasets(
    "BTIS3043_Dataset_A_Existing_eBook_Collection.xlsx",
    "BTIS3043_Dataset_B_Academic_eBook_Catalogue.xlsx",
    "BTIS3043_Dataset_C_eBook_Acquisition_Catalogue.xlsx",
)


# ---------------------------------------------------------------------------
# Generic pipeline: predicate filter -> fuzzy score -> ranked table
# ---------------------------------------------------------------------------
def run_pipeline(df, classify_fn, title_col, year_col, price_col=None,
                  fmt_col=None, weights_with_price=(0.45, 0.25, 0.30),
                  weights_no_price=(0.6, 0.3, 0.1)):
    records = []
    for _, row in df.iterrows():
        res = classify_fn(row)
        if not res["passes"]:
            continue
        rec = dict(row)
        rec.update(res)
        records.append(rec)

    if not records:
        return pd.DataFrame()

    cand = pd.DataFrame(records)

    rel = cand["tier"].apply(fuzzy_relevance_from_tier)
    rec_fz = cand[year_col].apply(fuzzy_recency)

    if price_col is not None and price_col in cand.columns and cand[price_col].notna().any():
        lo, hi = cand[price_col].min(), cand[price_col].max()
        aff = cand[price_col].apply(lambda p: fuzzy_affordability(p, lo, hi))
        if fmt_col is not None and fmt_col in cand.columns:
            fmt = cand[fmt_col].apply(fuzzy_format_suitability)
            score = [weighted_fuzzy_score([r, rc, a, f], [0.4, 0.2, 0.25, 0.15])
                     for r, rc, a, f in zip(rel, rec_fz, aff, fmt)]
        else:
            w = weights_with_price
            score = [weighted_fuzzy_score([r, rc, a], w) for r, rc, a in zip(rel, rec_fz, aff)]
        cand["fuzzy_affordability"] = aff
    else:
        if fmt_col is not None and fmt_col in cand.columns:
            fmt = cand[fmt_col].apply(fuzzy_format_suitability)
            w = weights_no_price
            score = [weighted_fuzzy_score([r, rc, f], w) for r, rc, f in zip(rel, rec_fz, fmt)]
            cand["fuzzy_format"] = fmt
        else:
            score = [weighted_fuzzy_score([r, rc], [0.7, 0.3]) for r, rc in zip(rel, rec_fz)]

    cand["fuzzy_relevance"] = rel
    cand["fuzzy_recency"] = rec_fz
    cand["fuzzy_score"] = score

    predicate_only = cand[[title_col, "category", "tier"]].reset_index(drop=True)
    predicate_only.insert(0, "No", range(1, len(predicate_only) + 1))

    keep_cols = [title_col, "category", "fuzzy_relevance", "fuzzy_recency"]
    if "fuzzy_affordability" in cand.columns:
        keep_cols.append("fuzzy_affordability")
    if "fuzzy_format" in cand.columns:
        keep_cols.append("fuzzy_format")
    keep_cols.append("fuzzy_score")
    fuzzy_ranked = add_rank(cand[keep_cols], "fuzzy_score")

    return predicate_only, fuzzy_ranked, cand


# ---------------------------------------------------------------------------
# SCENARIO 1
# ---------------------------------------------------------------------------
print("=" * 90)
print("SCENARIO 1: Artificial Intelligence, Programming & Mathematical Foundations")
print("=" * 90)

pA1, fA1, _ = run_pipeline(A, classify_A_scenario1, "Title", "Copyright Year",
                            price_col="Unit Net Price")
print("\n--- Dataset A: predicate-only ---")
print(pA1.to_string(index=False) if len(pA1) else "(no records)")
print("\n--- Dataset A: fuzzy-enhanced (top 5) ---")
print(fA1.head(5).to_string(index=False) if len(fA1) else "(no records)")

pB1, fB1, _ = run_pipeline(B, classify_B_scenario1, "Title", "Copyright",
                            fmt_col="eBook Format")
print(f"\n--- Dataset B: predicate-only ({len(pB1)} matched) ---")
print("\n--- Dataset B: fuzzy-enhanced (top 5) ---")
print(fB1.head(5).to_string(index=False) if len(fB1) else "(no records)")

pC1, fC1, _ = run_pipeline(C, classify_C_scenario1, "Title", "Copyright Year",
                            price_col="Single user / 1-Year", fmt_col="eBook Format")
print(f"\n--- Dataset C: predicate-only ({len(pC1)} matched) ---")
print("\n--- Dataset C: fuzzy-enhanced (top 5) ---")
print(fC1.head(5).to_string(index=False) if len(fC1) else "(no records)")

# ---------------------------------------------------------------------------
# SCENARIO 2
# ---------------------------------------------------------------------------
print("\n\n" + "=" * 90)
print("SCENARIO 2: Cybersecurity and Secure Computing")
print("=" * 90)

pA2, fA2, _ = run_pipeline(A, classify_A_scenario2, "Title", "Copyright Year",
                            price_col="Unit Net Price")
print("\n--- Dataset A: predicate-only (ALL, = current subscription) ---")
print(pA2.to_string(index=False) if len(pA2) else "(no records)")
print("\n--- Dataset A: fuzzy-enhanced (ALL, = current subscription) ---")
print(fA2.to_string(index=False) if len(fA2) else "(no records)")

pB2, fB2, _ = run_pipeline(B, classify_B_scenario2, "Title", "Copyright",
                            fmt_col="eBook Format")
print(f"\n--- Dataset B: predicate-only ({len(pB2)} matched) ---")
print("\n--- Dataset B: fuzzy-enhanced (top 10) ---")
print(fB2.head(10).to_string(index=False) if len(fB2) else "(no records)")

pC2, fC2, _ = run_pipeline(C, classify_C_scenario2, "Title", "Copyright Year",
                            price_col="Single user / 1-Year", fmt_col="eBook Format")
print(f"\n--- Dataset C: predicate-only ({len(pC2)} matched) ---")
print("\n--- Dataset C: fuzzy-enhanced (top 10) ---")
print(fC2.head(10).to_string(index=False) if len(fC2) else "(no records)")

# ---------------------------------------------------------------------------
# Save all tables to CSV for the report
# ---------------------------------------------------------------------------
out = {
    "s1_A_predicate": pA1, "s1_A_fuzzy": fA1,
    "s1_B_predicate": pB1, "s1_B_fuzzy": fB1,
    "s1_C_predicate": pC1, "s1_C_fuzzy": fC1,
    "s2_A_predicate": pA2, "s2_A_fuzzy": fA2,
    "s2_B_predicate": pB2, "s2_B_fuzzy": fB2,
    "s2_C_predicate": pC2, "s2_C_fuzzy": fC2,
}
for name, d in out.items():
    d.to_csv(f"results_{name}.csv", index=False)

print("\n\nAll result tables saved as results_*.csv")

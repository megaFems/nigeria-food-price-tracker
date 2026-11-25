"""Checks on the price indices. Any failure stops the run with a clear message."""
import numpy as np
import pandas as pd


def run_checks(items: pd.DataFrame, basket: pd.DataFrame, marked: pd.DataFrame) -> pd.DataFrame:
    from clean_wfp import KNOWN_GAP
    from indices import ALL_AREAS, BASE, MIN_ITEMS, MIN_MARKETS
    from suspects import INDEX_ITEMS, REASONS, START

    problems = []
    for name, t, key in (("items", items, ["area", "commodity"]), ("basket", basket, ["area"])):
        if t.duplicated(key + ["month"]).any():
            problems.append(f"{name}: duplicate months")
        if not (np.isfinite(t["index"]) & (t["index"] > 0)).all():
            problems.append(f"{name}: index missing or not positive")
        at_base = t[t["month"].isin(BASE.to_timestamp())].groupby(key)["index"].apply(lambda s: np.exp(np.log(s).mean()))
        if not np.allclose(at_base, 100):
            problems.append(f"{name}: base period does not average 100")
    if (items["markets"] < MIN_MARKETS).any():
        problems.append("an item month has too few markets")
    if (basket["items_used"] < MIN_ITEMS).any():
        problems.append("a basket month has too few items")

    ne_items = set(items.loc[items["area"] == ALL_AREAS, "commodity"])
    if ne_items != set(INDEX_ITEMS):
        problems.append(f"North-East items differ from the index items: {sorted(set(INDEX_ITEMS) ^ ne_items)}")
    gap = pd.to_datetime(list(KNOWN_GAP))
    ne = set(basket.loc[basket["area"] == ALL_AREAS, "month"])
    want = [m for m in pd.date_range(START.to_timestamp(), max(ne), freq="MS") if not gap[0] <= m <= gap[1]]
    missing = [str(m.date()) for m in want if m not in ne]
    if missing:
        problems.append(f"North-East basket missing in {len(missing)} months: {missing[:6]}")

    if not set(marked["suspect"]) <= {"", *REASONS}:
        problems.append("unknown suspect reason")
    if marked.loc[marked["is_outlier"] | ~marked["commodity"].isin(INDEX_ITEMS), "suspect"].eq("").any():
        problems.append("an outlier or left-out food is counted as clean")

    if problems:
        raise AssertionError("indices failed checks:\n- " + "\n- ".join(problems))
    return pd.DataFrame({"check": ["no duplicates, all positive", "base period averages 100",
                                   f">= {MIN_MARKETS} markets per item month, >= {MIN_ITEMS} items per basket month",
                                   "North-East covers all items and every month outside the gap"], "result": "ok"})

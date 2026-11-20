"""Checks on the clean North-East table. Any failure stops the run with a clear message."""
import pandas as pd

KEY = ["market_id", "month", "commodity_id"]


def run_checks(df: pd.DataFrame) -> pd.DataFrame:
    from clean_wfp import BASKET, BASKET_START, KNOWN_GAP, MAX_MISSING_MONTHS, STATES

    problems = []

    dupes = df.duplicated(KEY).sum()
    if dupes:   # also catches an actual and an aggregate price for the same market, month and item (D-004)
        problems.append(f"{dupes} rows share a market, month and item")

    if df["price_ngn"].isna().any() or (df["price_ngn"] <= 0).any():
        problems.append("missing, zero or negative prices")

    units_per_item = df.groupby("commodity")["unit"].nunique()
    mixed = units_per_item[units_per_item > 1]
    if len(mixed):
        problems.append(f"items with more than one pack size: {list(mixed.index)}")

    extra_states = set(df["state"]) - set(STATES)
    if extra_states:
        problems.append(f"unexpected states: {sorted(extra_states)}")

    # basket items: a price every month from BASKET_START, apart from the known gap and a few odd months
    months = pd.date_range(BASKET_START, df["month"].max(), freq="MS") + pd.Timedelta(days=14)
    months = [m for m in months if not (pd.Timestamp(KNOWN_GAP[0]) <= m <= pd.Timestamp(KNOWN_GAP[1]))]
    basket = df[df["in_basket"]]
    gaps = []
    for item in BASKET:
        have = set(basket.loc[basket["commodity"] == item, "month"])
        missing = [m.date() for m in months if m not in have]
        if len(missing) > MAX_MISSING_MONTHS:
            problems.append(f"{item}: no price in {len(missing)} months outside the known gap (first: {missing[0]})")
        gaps += [f"{item} {m}" for m in missing]

    if problems:
        raise AssertionError("clean table failed checks:\n- " + "\n- ".join(problems))

    return pd.DataFrame({
        "check": ["unique market-month-item", "prices positive", "one pack size per item",
                  "states", f"basket items monthly from {BASKET_START} (outside the known gap)"],
        "result": ["ok"] * 4 + [f"ok, {len(gaps)} odd missing item-months: {', '.join(gaps) or 'none'}"],
    })

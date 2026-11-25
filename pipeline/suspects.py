"""Mark suspected prices (D-016). They are reported and measured, but left out of every final figure.

Reasons, in the order they are given to a price:
  item      food not used in the indices at all (D-014)
  early     before September 2018: 13 Yobe foods look measured differently, so the region is not comparable (D-017)
  outlier   above 5x or below 1/5 of the item's median across markets that month (D-007)
  food mix  Yobe, May 2021: prices that look assigned to the wrong foods
  sheet     state month where the whole basket jumps over 20% and the next month undoes it (D-017)
  reversal  state month that jumps more than 3x and is undone by the next reading (D-013)
  state     state median more than 3x above (or below 1/3 of) both the readings before and the readings after
  market    the same test on one market's own prices
  price     one price more than 3x above (or below 1/3 of) the state's readings both before and after

"Before" and "after" are medians of up to 6 unsuspected readings within 12 months, at least 2 on each side (1 for `price`). The tests
repeat until nothing new is found. The most recent readings have no "after" yet, so the last three tests cannot cover them.
"""
import numpy as np
import pandas as pd

from clean_wfp import BASKET, BASKET_START

LEFT_OUT = {
    "Spinach": "the typical price sits near 50 naira for most of 2017 to 2023, and Borno has long gaps and an "
               "unexplained 5 to 9x stretch from April to November 2019",
}
INDEX_ITEMS = tuple(i for i in BASKET if i not in LEFT_OUT)
MIX = ("Yobe", pd.Period("2021-05", "M"), ("Bananas", "Eggs", "Oranges", "Spinach", "Sugar", "Watermelons"))
START = pd.Period("2018-09", "M")      # first month of the clean series
SHEET_JUMP, SHEET_NET, SHEET_ITEMS = 0.20, 0.10, 15
JUMP, REVERT, MIN_MATCHED, MAX_BACK = 3, 2, 3, 12
READINGS, WINDOW, MIN_SIDE = 6, 12, 2
REASONS = ("item", "early", "outlier", "food mix", "sheet", "reversal", "state", "market", "price")


def matched_changes(g: pd.DataFrame) -> list:
    """(month, change) against the latest earlier linked month within MAX_BACK that shares MIN_MATCHED markets."""
    wide = np.log(g.pivot(index="month", columns="market_id", values="price_per_std_unit")).sort_index()
    v, months, linked, out = wide.to_numpy(), list(wide.index), [0], []
    for i in range(1, len(months)):
        for j in reversed(linked):
            if (months[i] - months[j]).n > MAX_BACK:
                break
            d = v[i] - v[j]
            d = d[~np.isnan(d)]
            if len(d) >= MIN_MATCHED:
                out.append((months[i], float(np.exp(d.mean()))))
                linked.append(i)
                break
    return out


def reversals(df: pd.DataFrame) -> set:
    """State-item-months that jump and are undone by the next reading."""
    found = set()
    for (state, item), g in df.groupby(["state", "commodity"]):
        ch = matched_changes(g)
        for (m, a), (_, b) in zip(ch, ch[1:]):
            if (a > JUMP or a < 1 / JUMP) and (a > 1) != (b > 1) and 1 / REVERT <= a * b <= REVERT:
                found.add((state, item, m))
    return found


def sheets(df: pd.DataFrame) -> set:
    """State-months where the matched basket jumps more than SHEET_JUMP and the next month undoes it."""
    found = set()
    for state, g in df.groupby("state"):
        wide = np.log(g.pivot_table(index=["commodity", "market_id"], columns="month", values="price_per_std_unit"))
        move = {}
        for a, b in zip(wide.columns, wide.columns[1:]):
            d = (wide[b] - wide[a]).dropna().groupby("commodity").agg(["mean", "size"])
            d = d.loc[d["size"] >= MIN_MATCHED, "mean"]
            if (b - a).n == 1 and len(d) >= SHEET_ITEMS:
                move[b] = float(np.exp(d.mean()) - 1)
        for m, x in move.items():
            y = move.get(m + 1)
            if y is not None and abs(x) > SHEET_JUMP and abs((1 + x) * (1 + y) - 1) < SHEET_NET:
                found.add((state, m))
    return found


def out_of_line(t: np.ndarray, v: np.ndarray, ok: np.ndarray) -> np.ndarray:
    """True where v (log price at time t) is JUMP away, in the same direction, from before and after."""
    hit, lim = np.zeros(len(v), bool), np.log(JUMP)
    for k in np.flatnonzero(ok):
        before = v[ok & (t < t[k]) & (t >= t[k] - WINDOW)][-READINGS:]
        after = v[ok & (t > t[k]) & (t <= t[k] + WINDOW)][:READINGS]
        if len(before) >= MIN_SIDE and len(after) >= MIN_SIDE:
            d = v[k] - np.array([np.median(before), np.median(after)])
            hit[k] = (d > lim).all() or (d < -lim).all()
    return hit


def off_state(g: pd.DataFrame, med: pd.DataFrame) -> np.ndarray:
    """Rows of g that sit JUMP away from the state's monthly medians on both sides."""
    t, v = med["t"].to_numpy(), med["log_price"].to_numpy()
    sides = {}
    for k in g["t"].unique():
        before, after = v[(t < k) & (t >= k - WINDOW)][-READINGS:], v[(t > k) & (t <= k + WINDOW)][:READINGS]
        enough = len(before) and len(after)      # one state median is already many prices
        sides[k] = (np.median(before), np.median(after)) if enough else (np.nan, np.nan)
    d = g["log_price"].to_numpy()[:, None] - np.array([sides[k] for k in g["t"]])
    return (d > np.log(JUMP)).all(axis=1) | (d < -np.log(JUMP)).all(axis=1)


def mark(df: pd.DataFrame) -> pd.DataFrame:
    """Basket prices from BASKET_START with a `suspect` reason ('' when clean)."""
    df = df[df["in_basket"] & (df["month"] >= pd.Period(BASKET_START, "M"))].sort_values(["month", "market_id"]).copy()
    df["suspect"] = ""

    def give(hit, reason):
        df.loc[hit & df["suspect"].eq(""), "suspect"] = reason

    give(df["commodity"].isin(LEFT_OUT), "item")
    give(df["month"] < START, "early")
    give(df["is_outlier"], "outlier")
    give(df["state"].eq(MIX[0]) & df["month"].eq(MIX[1]) & df["commodity"].isin(MIX[2]), "food mix")
    bad_sheets = sheets(df[~df["is_outlier"] & ~df["commodity"].isin(LEFT_OUT)])
    give(pd.Series([k in bad_sheets for k in zip(df["state"], df["month"])], index=df.index), "sheet")
    rev = reversals(df[~df["is_outlier"] & ~df["commodity"].isin(LEFT_OUT)])
    give(pd.Series([k in rev for k in zip(df["state"], df["commodity"], df["month"])], index=df.index), "reversal")

    df["t"] = df["month"].map(lambda p: p.ordinal)
    df["log_price"] = np.log(df["price_per_std_unit"])
    for _ in range(20):
        before = df["suspect"].ne("").sum()
        clean = df[df["suspect"].eq("")]
        med = clean.groupby(["state", "commodity", "t"])["log_price"].median().reset_index()
        bad = set()
        for (s, c), g in med.groupby(["state", "commodity"]):
            hit = out_of_line(g["t"].to_numpy(), g["log_price"].to_numpy(), np.ones(len(g), bool))
            bad |= {(s, c, t) for t in g["t"].to_numpy()[hit]}
        give(pd.Series([k in bad for k in zip(df["state"], df["commodity"], df["t"])], index=df.index), "state")
        hits = []
        for _, g in df[df["suspect"].eq("")].groupby(["market_id", "commodity"]):
            hit = out_of_line(g["t"].to_numpy(), g["log_price"].to_numpy(), np.ones(len(g), bool))
            hits.extend(g.index[hit])
        give(df.index.isin(hits), "market")
        hits = []
        for (s, c), g in df[df["suspect"].eq("")].groupby(["state", "commodity"]):
            hits.extend(g.index[off_state(g, med[(med["state"] == s) & (med["commodity"] == c)])])
        give(df.index.isin(hits), "price")
        if df["suspect"].ne("").sum() == before:
            return df.drop(columns=["t", "log_price"])
    raise RuntimeError("suspect tests did not settle")

"""Price indices for the North-East basket (D-012, D-014, D-016, D-017).

Item index, per item and area: log(price) = month effect + market effect, fitted by least squares. The market
effects absorb markets that are usually dear or cheap, so markets joining or leaving do not move the index.
Basket index: the same fit on the item indices (month effect + item effect), each item with equal weight.
Both are scaled so the geometric mean over September 2018 to August 2019 is 100.

Final figures use clean prices only. The same indices with every price kept are saved for comparison.

Usage:  python pipeline/indices.py
"""
import pathlib
import sys

import numpy as np
import pandas as pd

from clean_wfp import OUT as CLEAN
from suspects import REASONS, mark

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT_ITEMS = PROCESSED / "index_items.parquet"
OUT_BASKET = PROCESSED / "index_basket.parquet"
OUT_ITEMS_ALL = PROCESSED / "index_items_all_prices.parquet"
OUT_BASKET_ALL = PROCESSED / "index_basket_all_prices.parquet"
OUT_MARKED = PROCESSED / "basket_prices_marked.parquet"
OUT_EFFECTS = PROCESSED / "suspect_effects.parquet"

ALL_AREAS = "North-East"
BASE = pd.period_range("2018-09", "2019-08", freq="M")
MIN_BASE = 6          # base-period months a series needs
MIN_MARKETS = 3       # markets a month needs
MIN_ITEMS = 20        # items a basket month needs


def load_marked() -> pd.DataFrame:
    df = pd.read_parquet(CLEAN)
    df["month"] = pd.to_datetime(df["month"]).dt.to_period("M")
    return mark(df)


def dummy_index(g: pd.DataFrame, unit: str, value: str) -> pd.Series:
    """Month effects of log(value) = month + unit, scaled to the base period."""
    mi, months = pd.factorize(g["month"], sort=True)
    ui, units = pd.factorize(g[unit], sort=True)
    if len(set(months) & set(BASE)) < MIN_BASE:
        return pd.Series(np.nan, index=months)
    x = np.zeros((len(g), len(months) + len(units)))
    x[np.arange(len(g)), mi] = 1
    x[np.arange(len(g)), len(months) + ui] = 1
    beta, _, rank, _ = np.linalg.lstsq(x, np.log(g[value].to_numpy()), rcond=None)
    if rank != x.shape[1] - 1:
        raise ValueError(f"months are not all connected through shared {unit}")
    s = pd.Series(beta[:len(months)], index=months)
    return 100 * np.exp(s - s[s.index.isin(BASE)].mean())


def yoy(index: pd.Series) -> np.ndarray:
    prev = index.copy()
    prev.index = prev.index + 12
    return (100 * (index / prev.reindex(index.index) - 1)).to_numpy()


def build(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = pd.concat([prices.assign(area=prices["state"]), prices.assign(area=ALL_AREAS)], ignore_index=True)
    items = []
    for (area, item), g in data.groupby(["area", "commodity"]):
        g = g[g.groupby("month")["market_id"].transform("nunique") >= MIN_MARKETS]
        if g.empty:
            continue
        s = dummy_index(g, "market_id", "price_per_std_unit").dropna()
        if s.empty:
            continue
        items.append(pd.DataFrame({"area": area, "commodity": item, "month": s.index, "index": s.to_numpy(),
                                   "markets": g.groupby("month")["market_id"].nunique().reindex(s.index).to_numpy(),
                                   "yoy_pct": yoy(s)}))
    items = pd.concat(items, ignore_index=True)

    basket = []
    for area, g in items.groupby("area"):
        g = g[g.groupby("month")["commodity"].transform("nunique") >= MIN_ITEMS]
        if g.empty:
            continue
        s = dummy_index(g, "commodity", "index").dropna()
        if not s.empty:
            basket.append(pd.DataFrame({"area": area, "month": s.index, "index": s.to_numpy(),
                                        "items_used": g.groupby("month").size().reindex(s.index).to_numpy(),
                                        "yoy_pct": yoy(s)}))
    basket = pd.concat(basket, ignore_index=True)
    for t in (items, basket):
        t["month"] = t["month"].dt.to_timestamp()
    return items, basket


def effects(marked: pd.DataFrame, basket: pd.DataFrame) -> pd.DataFrame:
    """Change in the North-East basket if one group of suspects were put back."""
    ne = lambda b: b[b["area"] == ALL_AREAS].set_index("month")["index"]
    clean = ne(basket)
    rows = []
    for reason in (*REASONS, "all suspects"):
        back = marked["suspect"].ne("") if reason == "all suspects" else marked["suspect"].eq(reason)
        pct = 100 * (ne(build(marked[marked["suspect"].eq("") | back])[1]) / clean - 1)
        top = pct.abs().idxmax()
        rows.append({"reason": reason, "prices": int(back.sum()), "largest_month": top, "largest_pct": pct[top],
                     "latest_pct": pct[clean.index.max()]})
    return pd.DataFrame(rows)


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from checks.check_indices import run_checks

    marked = load_marked()
    items, basket = build(marked[marked["suspect"].eq("")])
    print(run_checks(items, basket, marked).to_string(index=False))
    items_all, basket_all = build(marked)
    fx = effects(marked, basket)
    marked = marked.assign(month=marked["month"].dt.to_timestamp())
    for t, path in ((items, OUT_ITEMS), (basket, OUT_BASKET), (items_all, OUT_ITEMS_ALL), (basket_all, OUT_BASKET_ALL),
                    (marked, OUT_MARKED), (fx, OUT_EFFECTS)):
        t.to_parquet(path, index=False)
    print(f"\neffect of putting suspects back (North-East basket):\n{fx.round({'largest_pct': 1, 'latest_pct': 1}).to_string(index=False)}")
    print(f"\n{marked['suspect'].ne('').sum():,} of {len(marked):,} basket prices are suspected")


if __name__ == "__main__":
    main()

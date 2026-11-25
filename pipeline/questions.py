"""Answer the project's three questions from clean prices and write reports/findings.md with two charts.

1. Basket cost: one pack of each food at a typical North-East market of the last 12 months, carried back with the item indices.
2. Places: each market's last 6 months against the same months a year earlier, same foods, equal weights.
3. Unusual moves: the largest 3-month moves of the basket, and foods that moved far outside their usual range in both
   Borno and Yobe at once.

Usage:  python pipeline/questions.py   (run pipeline/indices.py first)
"""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from clean_wfp import KNOWN_GAP
from indices import ALL_AREAS, OUT_BASKET, OUT_ITEMS, OUT_MARKED, PROCESSED

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "findings.md"
FIGS = ROOT / "reports" / "figures"
OUT_COST = PROCESSED / "basket_cost.parquet"
OUT_MARKETS = PROCESSED / "market_changes.parquet"
CREDIT = "Source: WFP via HDX (CC BY-IGO). Clean prices only."
MIN_MARKET_ITEMS, MIN_MONTHS = 15, 3      # a market needs this many foods, each with this many matching months
STEP, BIG = 3, 3                          # months in a move; robust standard deviations that count as unusual
MIN_MARKETS = 5                           # markets behind an item index at both ends of an unusual move


def load():
    marked = pd.read_parquet(OUT_MARKED)
    return marked[marked["suspect"].eq("")], pd.read_parquet(OUT_ITEMS), pd.read_parquet(OUT_BASKET)


def basket_cost(clean: pd.DataFrame, items: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Naira cost of one pack of each food per month; months missing a food are left blank."""
    wide = items[items["area"] == ALL_AREAS].pivot(index="month", columns="commodity", values="index")
    recent = clean[clean["month"] > wide.index.max() - pd.DateOffset(months=12)]
    index = wide.stack().rename("index")
    r = recent.join(index, on=["month", "commodity"])
    base = (r["price_ngn"] / (r["index"] / 100)).groupby(r["commodity"]).median()
    parts = wide.mul(base, axis=1) / 100
    cost = parts.sum(axis=1, skipna=False)
    return pd.DataFrame({"cost": cost, "foods": wide.notna().sum(axis=1)}), parts.iloc[-1]


def market_changes(clean: pd.DataFrame) -> pd.DataFrame:
    last = clean["month"].max()
    now = clean[clean["month"] > last - pd.DateOffset(months=6)]
    old = clean.assign(month=clean["month"] + pd.DateOffset(months=12))
    keys = ["market_id", "commodity", "month"]
    m = now.merge(old[keys + ["price_per_std_unit"]], on=keys, suffixes=("", "_old"))
    m["d"] = np.log(m["price_per_std_unit"] / m["price_per_std_unit_old"])
    g = m.groupby(["state", "market", "market_id", "commodity"])["d"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] >= MIN_MONTHS]
    out = g.groupby(["state", "market"])["mean"].agg(["mean", "std", "size"]).reset_index()
    out = out[out["size"] >= MIN_MARKET_ITEMS]
    se = 1.96 * out["std"] / np.sqrt(out["size"])
    pct = lambda x: 100 * (np.exp(x) - 1)
    return pd.DataFrame({"state": out["state"], "market": out["market"], "foods": out["size"], "change": pct(out["mean"]),
                         "low": pct(out["mean"] - se), "high": pct(out["mean"] + se)}).sort_values("change", ascending=False)


def basket_moves(basket: pd.DataFrame, items: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """Largest non-overlapping 3-month rises and falls, with the foods that contributed most."""
    s = basket[basket["area"] == ALL_AREAS].set_index("month")["index"].asfreq("MS")
    wide = np.log(items[items["area"] == ALL_AREAS].pivot(index="month", columns="commodity", values="index")).asfreq("MS")
    ch = (np.log(s) - np.log(s.shift(STEP))).dropna()
    rows = []
    for sign in (1, -1):
        left = (sign * ch).sort_values(ascending=False)
        for _ in range(n):
            end = left.index[0]
            start = end - pd.DateOffset(months=STEP)
            d = (wide.loc[end] - wide.loc[start]).dropna()
            top = (sign * d).sort_values(ascending=False).head(4).index
            rows.append({"from": start, "to": end, "change": 100 * (np.exp(ch[end]) - 1), "foods compared": len(d),
                         "moved that way": int((sign * d > 0).sum()),
                         "largest movers": ", ".join(f"{c} {100 * (np.exp(d[c]) - 1):+.0f}%" for c in top)})
            left = left[(left.index - end).map(lambda x: abs(x.days)) > 31 * STEP]
    return pd.DataFrame(rows)


def item_moves(items: pd.DataFrame) -> pd.DataFrame:
    """Foods whose 3-month change is BIG robust deviations from usual, and at least half as large in Borno and in Yobe."""
    rows = []
    for item, g in items.groupby("commodity"):
        w = np.log(g.pivot(index="month", columns="area", values="index")).asfreq("MS")
        k = g[g["area"] == ALL_AREAS].set_index("month")["markets"].asfreq("MS")
        if not {"Borno", "Yobe", ALL_AREAS} <= set(w.columns):
            continue
        ch = w - w.shift(STEP)
        ne = ch[ALL_AREAS].dropna()
        z = (ne - ne.median()) / (1.4826 * (ne - ne.median()).abs().median())
        for m in z.index[z.abs() > BIG]:
            same = all(ch.at[m, a] * ne[m] > 0 and abs(ch.at[m, a]) >= abs(ne[m]) / 2 for a in ("Borno", "Yobe"))
            if same and min(k[m], k[m - pd.DateOffset(months=STEP)]) >= MIN_MARKETS:
                pct = lambda x: 100 * (np.exp(x) - 1)
                rows.append({"commodity": item, "start": m - pd.DateOffset(months=STEP), "to": m, "change": pct(ne[m]),
                             "borno": pct(ch.at[m, "Borno"]), "yobe": pct(ch.at[m, "Yobe"]), "z": z[m]})
    d = pd.DataFrame(rows).sort_values("z", key=abs, ascending=False)
    keep = []                                           # one row per episode: strongest first
    for r in d.itertuples():
        if not any(r.commodity == q.commodity and abs((r.to - q.to).days) <= 31 * STEP for q in keep):
            keep.append(r)
    return pd.DataFrame(keep).drop(columns="Index")


def charts(cost: pd.DataFrame, markets: pd.DataFrame) -> None:
    s = cost["cost"].asfreq("MS")
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(s.index, s.values, linewidth=2.2)
    ax.axvspan(pd.Timestamp(KNOWN_GAP[0]), pd.Timestamp(KNOWN_GAP[1]), color="grey", alpha=0.15, label="no data")
    ax.yaxis.set_major_formatter(lambda v, _: f"₦{v:,.0f}")
    ax.set_ylim(0)
    ax.set_title("Cost of one pack of each of 24 foods, North-East Nigeria")
    ax.legend(frameon=False)
    fig.text(0.01, 0.01, CREDIT + " Months missing a food are blank.", fontsize=8, color="grey")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIGS / "basket_cost.png", dpi=150)
    plt.close(fig)

    d = markets.sort_values("change")
    fig, ax = plt.subplots(figsize=(8, 0.32 * len(d) + 1.6))
    y = [f"{m} ({s})" for m, s in zip(d["market"], d["state"])]
    ax.errorbar(d["change"], y, xerr=[d["change"] - d["low"], d["high"] - d["change"]], fmt="o", markersize=4, linewidth=1)
    ax.axvline(0, color="grey", linewidth=0.8)
    ax.set_xlabel("% change, last 6 months against a year earlier (bars: 95% range)")
    ax.set_title("Food price change by market")
    fig.text(0.01, 0.005, CREDIT, fontsize=8, color="grey")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGS / "markets_change.png", dpi=150)
    plt.close(fig)


def main() -> None:
    clean, items, basket = load()
    FIGS.mkdir(parents=True, exist_ok=True)
    cost, parts = basket_cost(clean, items)
    markets = market_changes(clean)
    moves, unusual = basket_moves(basket, items), item_moves(items)
    cost.reset_index().to_parquet(OUT_COST, index=False)
    markets.to_parquet(OUT_MARKETS, index=False)
    charts(cost, markets)

    last = cost.index.max()
    c = cost["cost"]
    first = c[(c.index >= "2018-09") & (c.index < "2019-09")]
    pack = clean.groupby("commodity")["unit"].first()
    ym = lambda t: t.dt.strftime("%Y-%m")
    p = lambda x: f"{x:+.1f}%"
    top = parts.sort_values(ascending=False)
    ne = items[(items["area"] == ALL_AREAS) & (items["month"] == last)].sort_values("index", ascending=False)
    yoy = ne.dropna(subset=["yoy_pct"]).sort_values("yoy_pct", ascending=False)
    b = basket[basket["month"] == last].set_index("area")
    clear = int(((markets["low"] > 0) | (markets["high"] < 0)).sum())
    mt = markets.assign(change=markets["change"].map(p), range=[f"{l:+.0f}% to {h:+.0f}%" for l, h in zip(markets["low"], markets["high"])])
    s = [
        "# Findings\n",
        f"_Generated by `pipeline/questions.py`. {CREDIT} North-East means Borno, Yobe and Adamawa (Adamawa until November 2025)._\n",
        "## 1. What does a basket of food cost?\n",
        f"One pack of each of {len(parts)} foods cost about **₦{first.mean():,.0f}** in the year from September 2018 and "
        f"**₦{c[last]:,.0f}** in {last:%B %Y}: **{c[last] / first.mean():.1f} times** as much. A year earlier it was "
        f"₦{c.get(last - pd.DateOffset(months=12), np.nan):,.0f} ({p(100 * (c[last] / c.get(last - pd.DateOffset(months=12), np.nan) - 1))}). "
        f"The highest month was {c.idxmax():%B %Y} (₦{c.max():,.0f}).\n",
        "![Basket cost](figures/basket_cost.png)\n",
        f"Largest parts of the latest cost: " + ", ".join(f"{i} ₦{top[i]:,.0f} ({pack[i]})" for i in top.index[:6]) + ".\n",
        f"The price index, where every food counts equally, gives {b.at[ALL_AREAS, 'index'] / 100:.1f} times and {p(b.at[ALL_AREAS, 'yoy_pct'])} "
        "over the year. The naira basket gives dearer packs more weight, so the two differ.\n",
        "## 2. Which foods and places rose fastest?\n",
        "**Foods, since the year from September 2018:** " + ", ".join(f"{r.commodity} {r.index_ / 100:.1f}x" for r in ne.rename(columns={"index": "index_"}).head(5).itertuples()) + ".",
        "**Foods, last 12 months:** " + ", ".join(f"{r.commodity} {p(r.yoy_pct)}" for r in yoy.head(4).itertuples())
        + "; falling most: " + ", ".join(f"{r.commodity} {p(r.yoy_pct)}" for r in yoy.tail(3).iloc[::-1].itertuples()) + ".",
        "**States, since the year from September 2018:** " + ", ".join(f"{a} {b.at[a, 'index'] / 100:.1f}x" for a in b.index if a != ALL_AREAS) + ".\n",
        f"**Markets, last year.** {len(markets)} markets have enough matching prices. For {clear} of them the direction is clear "
        "(the 95% range leaves out zero). Ranges overlap, so close ranks should not be read as real differences.\n",
        mt[["market", "state", "foods", "change", "range"]].to_markdown(index=False),
        "\n![Markets](figures/markets_change.png)\n",
        "## 3. Which price moves were unusual?\n",
        "Largest 3-month moves of the basket:\n",
        moves.assign(**{"from": ym(moves["from"]), "to": ym(moves["to"]), "change": moves["change"].map(p)}).to_markdown(index=False),
        f"\nFoods that moved more than {BIG} times their usual 3-month spread, in both Borno and Yobe ({len(unusual)} episodes, "
        "strongest 12 shown):\n",
        unusual.head(12).rename(columns={"start": "from"}).assign(**{"from": ym(unusual["start"].head(12)), "to": ym(unusual["to"].head(12)),
                                   **{k: unusual[k].head(12).map(p) for k in ("change", "borno", "yobe")},
                                   "z": unusual["z"].head(12).round(1)}).rename(columns={"z": "times usual spread"}).to_markdown(index=False),
        "\n## Limits\n",
        "- A move seen in two states is more likely real, but this does not prove it or show its cause.",
        "- Screening out suspected prices can also remove or soften real shocks.",
        "- The cost uses recent typical prices carried back with each food's index. It is an illustration, not a household budget.",
        "- The latest month has no later readings to test it against. Details: [indices_summary.md](indices_summary.md), [data_quality.md](data_quality.md).",
    ]
    REPORT.write_text("\n".join(s) + "\n", encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

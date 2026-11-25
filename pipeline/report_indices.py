"""Write reports/indices_summary.md and two charts. Findings use clean prices; suspects are shown for comparison.

Usage:  python pipeline/report_indices.py   (run pipeline/indices.py first)
"""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from clean_wfp import KNOWN_GAP
from indices import ALL_AREAS, OUT_BASKET, OUT_BASKET_ALL, OUT_EFFECTS, OUT_ITEMS, OUT_ITEMS_ALL, OUT_MARKED
from suspects import LEFT_OUT

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "indices_summary.md"
FIGS = ROOT / "reports" / "figures"
CREDIT = "Source: WFP via HDX (CC BY-IGO). Time-dummy index, September 2018 to August 2019 = 100. Clean prices only unless marked."
CAUTION_PCT = 3       # months where suspects would move the North-East basket by this much are shaded
REASON_TEXT = {
    "item": "spinach, not used at all", "early": "before September 2018 (Yobe measured differently)",
    "sheet": "state month where the whole basket jumps, then comes back", "outlier": "far from other markets that month",
    "food mix": "Yobe, May 2021: other foods' prices", "reversal": "state month that jumps, then comes back",
    "state": "state 3x off both before and after (all sugar)", "market": "market 3x off both before and after",
    "price": "single price 3x off the state both before and after", "all suspects": "**everything suspected**",
}


def pct(x: float) -> str:
    return "n/a" if pd.isna(x) else f"{x:+.1f}%"


def monthly(g: pd.DataFrame) -> pd.Series:
    s = g.set_index("month")["index"]
    return s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="MS"))     # leave gaps blank


def basket_chart(basket: pd.DataFrame, raw: pd.Series, caution: list, path: pathlib.Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for area, g in basket.groupby("area"):
        s = monthly(g)
        ax.plot(s.index, s.values, label=area, linewidth=2.5 if area == ALL_AREAS else 1.2)
    ax.plot(raw.index, raw.values, color="black", linestyle=":", linewidth=1.2, label=f"{ALL_AREAS}, suspects included")
    ax.axvspan(pd.Timestamp(KNOWN_GAP[0]), pd.Timestamp(KNOWN_GAP[1]), color="grey", alpha=0.15, label="no data")
    half = pd.Timedelta(days=15)
    for i, m in enumerate(caution):
        ax.axvspan(m - half, m + half, color="gold", alpha=0.35, linewidth=0,
                   label=f"suspects would move it {CAUTION_PCT}% or more" if i == 0 else None)
    ax.axhline(100, color="grey", linewidth=0.8)
    ax.set_title("Food basket price index, North-East Nigeria (September 2018 to August 2019 = 100)")
    ax.set_ylabel("index")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    fig.text(0.01, 0.01, CREDIT, fontsize=8, color="grey")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def items_chart(d: pd.DataFrame, month: str, path: pathlib.Path) -> None:
    d = d.sort_values("yoy_pct")
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(d["commodity"], d["yoy_pct"], color=["#c0504d" if v > 0 else "#4f81bd" for v in d["yoy_pct"]], label="clean prices")
    ax.scatter(d["yoy_all"], d["commodity"], color="black", s=18, zorder=3, label="suspects included")
    ax.axvline(0, color="grey", linewidth=0.8)
    ax.set_title(f"Price change over 12 months to {month}, North-East Nigeria")
    ax.set_xlabel("% change")
    ax.legend(frameon=False, loc="lower right")
    fig.text(0.01, 0.01, CREDIT, fontsize=7, color="grey")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    items, items_all = pd.read_parquet(OUT_ITEMS), pd.read_parquet(OUT_ITEMS_ALL)
    basket, basket_all = pd.read_parquet(OUT_BASKET), pd.read_parquet(OUT_BASKET_ALL)
    fx, marked = pd.read_parquet(OUT_EFFECTS), pd.read_parquet(OUT_MARKED)
    FIGS.mkdir(parents=True, exist_ok=True)

    both = basket.merge(basket_all[["area", "month", "index", "yoy_pct"]], on=["area", "month"], suffixes=("", "_all"), how="left")
    both["effect"] = 100 * (both["index_all"] / both["index"] - 1)
    ne = both[both["area"] == ALL_AREAS].set_index("month")
    last = ne.index.max()
    month = last.strftime("%B %Y")
    caution = list(ne.index[ne["effect"].abs() >= CAUTION_PCT])
    raw = monthly(basket_all[basket_all["area"] == ALL_AREAS])

    it = items.merge(items_all[["area", "commodity", "month", "index", "yoy_pct"]], on=["area", "commodity", "month"],
                     suffixes=("", "_all"), how="left").rename(columns={"yoy_pct_all": "yoy_all"})
    now = it[(it["area"] == ALL_AREAS) & (it["month"] == last)].copy()
    now["effect"] = 100 * (now["index_all"] / now["index"] - 1)
    share = marked.assign(s=marked["suspect"].ne("")).groupby("commodity")["s"].mean() * 100
    now["suspected"] = now["commodity"].map(share)
    now = now.sort_values("yoy_pct", ascending=False)

    basket_chart(basket, raw, caution, FIGS / "basket_index.png")
    items_chart(now.dropna(subset=["yoy_pct"]), month, FIGS / "items_yoy.png")

    n_sus, n = int(marked["suspect"].ne("").sum()), len(marked)
    spin = int(marked["suspect"].eq("item").sum())
    early = int(marked["suspect"].eq("early").sum())
    peak = ne["yoy_pct"].idxmax()
    states = both.sort_values("month").groupby("area").tail(1)
    worst = ne.loc[caution].copy()
    untested = int((marked["month"].eq(last) & marked["suspect"].eq("")).sum())
    s = [
        "# Price indices: findings\n",
        "_Generated by `pipeline/report_indices.py`. " + CREDIT + "_\n",
        "## Headline (clean prices only)\n",
        f"- In {month} the North-East food basket index was **{ne.at[last, 'index']:.1f}**: the same foods cost about "
        f"**{ne.at[last, 'index'] / 100:.1f} times** what they did in the year from September 2018.",
        f"- Over the last 12 months the basket changed by **{pct(ne.at[last, 'yoy_pct'])}**.",
        f"- The fastest annual rise was **{pct(ne.at[peak, 'yoy_pct'])}**, in {peak.strftime('%B %Y')}.\n",
        "![Basket index](figures/basket_index.png)\n",
        "## By state (latest month with a basket index)\n",
        pd.DataFrame({"area": states["area"], "month": states["month"].dt.strftime("%Y-%m"), "index": states["index"].round(1),
                      "12-month change": states["yoy_pct"].map(pct), "index with suspects": states["index_all"].round(1),
                      "effect of suspects": states["effect"].map(pct)}).to_markdown(index=False),
        f"\n## Items, North-East, {month}\n",
        pd.DataFrame({"food": now["commodity"], "index": now["index"].round(1), "12-month change": now["yoy_pct"].map(pct),
                      "12-month change with suspects": now["yoy_all"].map(pct), "effect of suspects on index": now["effect"].map(pct),
                      "prices suspected, all months": now["suspected"].map(lambda v: f"{v:.1f}%")}).to_markdown(index=False),
        "\n![Item changes](figures/items_yoy.png)\n",
        "## Suspected prices: shown, not counted\n",
        f"{n_sus:,} of {n:,} basket prices since July 2017 are suspected or not comparable ({n_sus / n:.1%}); {spin:,} of them are spinach and {early:,} are from before September 2018. They stay in "
        "the clean table and are left out of every figure above. Suspected does not mean proven wrong: some may be real.",
        "\nWhat putting each group back would do to the North-East basket:\n",
        pd.DataFrame({"group": fx["reason"].map(REASON_TEXT), "prices": fx["prices"],
                      "largest effect": fx["largest_pct"].map(pct), "in": fx["largest_month"].dt.strftime("%Y-%m"),
                      f"effect in {month}": fx["latest_pct"].map(pct)}).to_markdown(index=False),
        f"\nMonths where all suspects together would move it by {CAUTION_PCT}% or more (gold on the chart):\n",
        pd.DataFrame({"month": worst.index.strftime("%Y-%m"), "clean": worst["index"].round(1), "with suspects": worst["index_all"].round(1),
                      "effect": worst["effect"].map(pct), "12-month change, clean": worst["yoy_pct"].map(pct),
                      "12-month change, with suspects": worst["yoy_pct_all"].map(pct)}).to_markdown(index=False),
        "\n## How to read this\n",
        "Details of the gaps and inconsistent prices: [data_quality.md](data_quality.md).\n",
        "- Each item's index comes from one fit of month and market effects, so markets joining or leaving do not move it. "
        "Past values can shift slightly when new months are added.",
        f"- The tests compare a price with readings before and after, so the {untested} clean prices of {month} have not had them, and "
        "the months just before have only partly had them. The headline could change slightly as new months arrive.",
        "- Clean means no test raised a doubt; it does not prove a price is right. Early salt prices are uneven.",
        "- Adamawa has no basket index of its own; its markets count in the North-East until November 2025.",
        "- The basket gives each item equal weight; no consumption weights are available for this area. State baskets can hold "
        "fewer items than the North-East one (at least 20).",
        f"- There are no prices for most items from {KNOWN_GAP[0][:7]} to {KNOWN_GAP[1][:7]}; that stretch is left blank and shaded.",
        "- Not used: " + "; ".join(f"{k} ({v})" for k, v in LEFT_OUT.items()) + ".",
    ]
    REPORT.write_text("\n".join(s) + "\n", encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)} and 2 charts in {FIGS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

"""Nigeria Food Price Tracker: North-East dashboard.

Usage:  streamlit run dashboard/app.py
"""
import pathlib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA = pathlib.Path(__file__).parent / "data"
GAP = ("2022-06-01", "2023-01-31")
BASE = "September 2018 to August 2019 = 100"
CREDIT = "Source: World Food Programme, via the Humanitarian Data Exchange (CC BY-IGO). Analysis: Foluso Oluwafemi."
AREAS = ["North-East", "Borno", "Yobe"]
COLOURS = {"North-East": "#ff7f0e", "Borno": "#4c9be8", "Yobe": "#2ca02c"}
REASONS = {
    "item": "Food not used (spinach)", "early": "Before September 2018 (Yobe measured differently)",
    "outlier": "Far from other markets that month", "food mix": "Yobe, May 2021: other foods' prices",
    "sheet": "Whole survey jumps, then comes back", "reversal": "State month jumps, then comes back",
    "state": "State month 3x off before and after", "market": "Market's price 3x off before and after",
    "price": "Single price 3x off the state before and after",
}

st.set_page_config(page_title="Nigeria Food Price Tracker", layout="wide")


@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA / f"{name}.parquet")


def pick(name_clean: str, name_all: str, with_suspects: bool) -> pd.DataFrame:
    return load(name_all if with_suspects else name_clean)


def line_chart(series: dict, title: str, y_title: str, dotted: dict | None = None, money: bool = False) -> go.Figure:
    fig = go.Figure()
    for name, s in series.items():
        s = s.asfreq("MS")                    # gaps stay blank
        fig.add_scatter(x=s.index, y=s.values, name=name, mode="lines",
                        line={"width": 3 if name == "North-East" else 1.6, "color": COLOURS.get(name)})
    for name, s in (dotted or {}).items():
        s = s.asfreq("MS")
        fig.add_scatter(x=s.index, y=s.values, name=name, mode="lines", line={"dash": "dot", "color": "#9a9a9a", "width": 1.2})
    fig.add_vrect(x0=GAP[0], x1=GAP[1], fillcolor="grey", opacity=0.15, line_width=0, annotation_text="no data")
    fig.update_layout(title=title, yaxis_title=y_title, hovermode="x unified", legend={"orientation": "h", "y": -0.15},
                      margin={"t": 50, "b": 10})
    if money:
        fig.update_yaxes(tickprefix="₦", tickformat=",.0f")
    return fig


st.title("Food prices in North-East Nigeria")
st.caption("Borno, Yobe and Adamawa (Adamawa until November 2025). Monthly market prices, September 2018 onwards.")

basket, cost = load("index_basket"), load("basket_cost").set_index("month")["cost"]
ne = basket[basket["area"] == "North-East"].set_index("month")
last = ne.index.max()
year_ago = last - pd.DateOffset(months=12)
c1, c2, c3 = st.columns(3)
c1.metric(f"Basket price index, {last:%b %Y}", f"{ne.at[last, 'index']:.0f}", f"{ne.at[last, 'yoy_pct']:+.1f}% on a year ago",
          delta_color="inverse", help=BASE + ". 452 means 4.5 times the base year. Every food counts equally.")
c2.metric(f"24-food basket cost, {last:%b %Y}", f"₦{cost[last]:,.0f}",
          f"{100 * (cost[last] / cost[year_ago] - 1):+.1f}% on a year ago", delta_color="inverse",
          help="One pack of each of 24 foods at typical North-East prices; dearer packs count more than in the index.")
c3.metric("Clean prices used", f"{(load('prices')['suspect'] == '').sum():,}",
          help="Clean prices only. Suspected prices are shown in the Data quality tab, not counted.")

with st.sidebar:
    st.header("Options")
    with_suspects = st.toggle("Count suspected prices", value=False,
                              help="Off: clean prices only, as in the findings. On: every price, to see what the suspects change.")
    st.caption("Clean prices only is the official view." if not with_suspects else "Showing every price. Not the official figures.")

tab_basket, tab_food, tab_markets, tab_quality = st.tabs(["Basket", "Foods", "Markets", "Data quality"])

with tab_basket:
    b = pick("index_basket", "index_basket_all_prices", with_suspects)
    b = b[b["month"] >= "2018-09-01"]
    areas = st.multiselect("Areas", AREAS, default=AREAS)
    series = {a: b[b["area"] == a].set_index("month")["index"] for a in areas}
    dotted = {}
    if not with_suspects and "North-East" in areas:
        a = load("index_basket_all_prices")
        dotted = {"North-East, suspects counted": a[(a["area"] == "North-East") & (a["month"] >= "2018-09-01")].set_index("month")["index"]}
    st.plotly_chart(line_chart(series, f"Food basket price index ({BASE})", "index", dotted), width="stretch")
    st.plotly_chart(line_chart({"North-East": cost}, "Cost of one pack of each of 24 foods", "naira", money=True),
                    width="stretch")
    st.caption("Months where a food has no clean price are left blank.")

with tab_food:
    items = pick("index_items", "index_items_all_prices", with_suspects)
    items = items[items["month"] >= "2018-09-01"]
    foods = sorted(items["commodity"].unique())
    c1, c2 = st.columns([2, 1])
    chosen = c1.multiselect("Foods", foods, default=["Rice (local)", "Eggs", "Oil (vegetable)"])
    area = c2.selectbox("Area", AREAS)
    sub = items[items["area"] == area]
    st.plotly_chart(line_chart({f: sub[sub["commodity"] == f].set_index("month")["index"] for f in chosen},
                               f"Food price index, {area} ({BASE})", "index"), width="stretch")
    month = st.select_slider("Month for the table", options=sorted(sub["month"].unique()), value=sub["month"].max(),
                             format_func=lambda m: f"{pd.Timestamp(m):%b %Y}")
    t = sub[sub["month"] == month][["commodity", "index", "yoy_pct", "markets"]].sort_values("yoy_pct", ascending=False)
    st.dataframe(t.rename(columns={"commodity": "food", "yoy_pct": "change on a year ago (%)", "markets": "markets reporting"}),
                 hide_index=True, width="stretch",
                 column_config={"index": st.column_config.NumberColumn(format="%.0f"),
                                "change on a year ago (%)": st.column_config.NumberColumn(format="%+.1f")})

with tab_markets:
    m = load("market_changes").sort_values("change")
    st.write("Each market's last 6 months against the same months a year earlier, same foods, equal weights. "
             "Bars are 95% ranges: where they cross zero, the direction is not clear.")
    fig = go.Figure(go.Scatter(x=m["change"], y=m["market"] + " (" + m["state"] + ")", mode="markers",
                               error_x={"type": "data", "symmetric": False, "array": m["high"] - m["change"],
                                        "arrayminus": m["change"] - m["low"]}))
    fig.add_vline(x=0, line_color="grey")
    fig.update_layout(xaxis_title="% change on a year ago", height=30 * len(m) + 120, margin={"t": 20})
    st.plotly_chart(fig, width="stretch")
    if with_suspects:
        st.caption("This view uses clean prices only.")

with tab_quality:
    p = load("prices")
    sus = p[p["suspect"] != ""]
    st.write(f"{len(sus):,} of {len(p):,} prices since July 2017 are suspected or not comparable. They are kept and shown here, "
             "but not counted. Suspected does not mean proven wrong.")
    fx = load("suspect_effects")
    fx = fx.assign(group=fx["reason"].map({**REASONS, "all suspects": "All of them"}))
    st.dataframe(fx[["group", "prices", "largest_pct", "largest_month", "latest_pct"]].rename(columns={
        "largest_pct": "largest effect on the basket (%)", "largest_month": "in", "latest_pct": f"effect in {last:%B %Y} (%)"}),
        hide_index=True, width="stretch",
        column_config={"in": st.column_config.DateColumn(format="MMM YYYY"),
                       "largest effect on the basket (%)": st.column_config.NumberColumn(format="%+.1f"),
                       f"effect in {last:%B %Y} (%)": st.column_config.NumberColumn(format="%+.1f")})
    c1, c2, c3 = st.columns(3)
    r = c1.selectbox("Reason", ["All"] + [REASONS[k] for k in REASONS if k in set(sus["suspect"])])
    f = c2.selectbox("Food", ["All"] + sorted(sus["commodity"].unique()))
    s = c3.selectbox("State", ["All"] + sorted(sus["state"].unique()))
    v = sus.assign(reason=sus["suspect"].map(REASONS))
    v = v[(r == "All") | (v["reason"] == r)]
    v = v[(f == "All") | (v["commodity"] == f)]
    v = v[(s == "All") | (v["state"] == s)]
    st.dataframe(v[["month", "state", "market", "commodity", "unit", "price_ngn", "reason"]].sort_values("month", ascending=False),
                 hide_index=True, width="stretch",
                 column_config={"month": st.column_config.DateColumn(format="MMM YYYY"),
                                "price_ngn": st.column_config.NumberColumn("price (naira)", format="%,.0f")})

st.divider()
st.caption(CREDIT + " Prices are from markets in areas affected by conflict; some months and foods are missing.")

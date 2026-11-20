"""Clean the WFP prices for the North-East (phase 1) into one tidy table.

One row per market, month and item (retail prices, Borno, Yobe and Adamawa, 2016 onwards), with:
- the published pack price and a price per standard unit (kg, litre or piece)
- in_basket: one of the 25 items with unbroken series (D-005)
- is_outlier: above 5x or below 1/5 of the item's median across markets that month (D-007)
- markets_reporting / low_coverage: how many markets reported the item that month (D-009)

Writes data/processed/wfp_ne_retail_clean.parquet.

Usage:  python pipeline/clean_wfp.py
"""
import pathlib
import re

import duckdb
import pandas as pd

from profile_wfp import latest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "wfp_ne_retail_clean.parquet"

STATES = ("Borno", "Yobe", "Adamawa")
START = "2016-01-01"
BASKET_START = "2017-07-01"                 # every basket item has prices from here (D-011)
KNOWN_GAP = ("2022-06-01", "2023-01-31")    # 20 of 25 basket items have no prices in these 8 months (D-011)
MAX_MISSING_MONTHS = 2                      # outside the gap, per basket item
OUTLIER_RATIO = 5
MIN_MARKETS = 10
BASKET = (
    "Bananas", "Beans (red)", "Beans (white)", "Cowpeas", "Eggs", "Fish", "Groundnuts", "Maize flour",
    "Meat (beef)", "Meat (goat)", "Milk (powder)", "Millet", "Oil (palm)", "Oil (vegetable)", "Onions",
    "Oranges", "Rice (imported)", "Rice (local)", "Salt", "Sorghum", "Spinach", "Sugar", "Tomatoes",
    "Watermelons", "Yam",
)

# unit text -> (standard unit, how many standard units in one pack)
_UNIT = re.compile(r"^\s*(\d+(?:\.\d+)?)?\s*(KG|G|L|pcs|Unit|Tubers)\s*$", re.IGNORECASE)
_STD = {"kg": ("kg", 1.0), "g": ("kg", 0.001), "l": ("litre", 1.0), "pcs": ("piece", 1.0),
        "unit": ("piece", 1.0), "tubers": ("piece", 1.0)}


def parse_unit(unit: str) -> tuple[str, float]:
    m = _UNIT.match(unit)
    if not m:
        raise ValueError(f"unknown unit: {unit!r}")
    qty = float(m.group(1)) if m.group(1) else 1.0
    std, factor = _STD[m.group(2).lower()]
    return std, qty * factor


def load_raw(con: duckdb.DuckDBPyConnection) -> None:
    path = latest("wfp_food_prices_nga")
    states = ", ".join(f"'{s}'" for s in STATES)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw AS
        SELECT CAST(date AS DATE) AS month, admin1 AS state, admin2 AS lga, market, CAST(market_id AS INTEGER) AS market_id,
               CAST(latitude AS DOUBLE) AS latitude, CAST(longitude AS DOUBLE) AS longitude,
               category, commodity, CAST(commodity_id AS INTEGER) AS commodity_id, unit, priceflag,
               CAST(price AS DOUBLE) AS price_ngn
        FROM read_csv('{path.as_posix()}', header=true, all_varchar=true)
        WHERE date NOT LIKE '#%' AND pricetype = 'Retail' AND currency = 'NGN'
          AND admin1 IN ({states}) AND CAST(date AS DATE) >= DATE '{START}'
    """)


def clean() -> pd.DataFrame:
    con = duckdb.connect()
    load_raw(con)

    units = con.execute("SELECT DISTINCT unit FROM raw").df()
    units[["std_unit", "units_per_pack"]] = units["unit"].apply(lambda u: pd.Series(parse_unit(u)))
    con.register("units", units)
    con.register("basket", pd.DataFrame({"commodity": BASKET}))

    df = con.execute(f"""
        WITH priced AS (
            SELECT r.*, u.std_unit, u.units_per_pack, r.price_ngn / u.units_per_pack AS price_per_std_unit
            FROM raw r JOIN units u USING (unit)
        ),
        month_stats AS (
            SELECT month, commodity, MEDIAN(price_per_std_unit) AS median_price, COUNT(DISTINCT market_id) AS markets_reporting
            FROM priced GROUP BY ALL
        )
        SELECT p.month, p.state, p.lga, p.market, p.market_id, p.latitude, p.longitude,
               p.category, p.commodity, p.commodity_id, p.unit, p.std_unit, p.units_per_pack,
               p.price_ngn, p.price_per_std_unit, p.priceflag,
               p.commodity IN (SELECT commodity FROM basket) AS in_basket,
               p.price_per_std_unit > {OUTLIER_RATIO} * s.median_price
                 OR p.price_per_std_unit < s.median_price / {OUTLIER_RATIO} AS is_outlier,
               s.markets_reporting,
               s.markets_reporting < {MIN_MARKETS} AS low_coverage
        FROM priced p JOIN month_stats s USING (month, commodity)
        ORDER BY p.month, p.state, p.market, p.commodity
    """).df()
    return df


def main() -> pd.DataFrame:
    import sys
    sys.path.insert(0, str(ROOT))
    from checks.check_clean import run_checks

    df = clean()
    summary = run_checks(df)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.register("df", df)
    con.execute(f"COPY df TO '{OUT.as_posix()}' (FORMAT PARQUET)")
    print(summary.to_string(index=False))
    print(f"wrote {OUT.relative_to(ROOT)} ({len(df):,} rows)")
    return df


if __name__ == "__main__":
    main()

# Decisions

I record every choice that could change the results: what I decided, why, and what it affects. Entries are in the order
I made them. When a later decision replaces an earlier one, I keep the earlier entry and mark it, so the reasoning stays visible.

## D-001: Use WFP (HDX) as the first source, downloaded by script (2026-11-16)
- **Decision:** I start with the WFP "Nigeria - Food Prices" dataset from HDX.
- **Why:** it has an open licence (CC BY-IGO), a stable API, monthly updates and history back to 2002. NBS data needs a login.
- **Affects:** `pipeline/ingest_wfp.py`; the credit line "Source: WFP via HDX (CC BY-IGO)" on every chart.

## D-002: Scope, given WFP is not national after 2022 (2026-11-18)
WFP covers about 13 states up to 2022, but since 2023 only Borno and Yobe (plus Adamawa to 2025). I considered three options:
- **A. National tracker:** add NBS Selected Food Price Watch as the main source and use WFP for long history and the
  North-East. This needs an NBS account and downloads by hand.
- **B. North-East focus:** WFP only. Fully automatable, a rich basket and a strong humanitarian story, but not national.
- **C. Both, staged:** build B first, then add A as a second phase.
- **Decision: C.** Phase 1 is the North-East analysis on WFP data (Borno, Yobe, Adamawa). Phase 2 may add NBS for
  national coverage.
- **Later note (2026-11-25):** the NBS tables I checked give zone averages and the highest and lowest state, not every
  state, and they start in November 2024. Phase 2 needs a fresh look before I commit to it.
- **Later note (2026-11-26):** I checked other sources (NBS CPI, World Bank crowdsourced and Real Time Prices, FEWS NET).
  None gives current monthly prices for every state; each has limits, listed in the README.

## D-003: Never use WFP `usdprice` (2026-11-16)
- **Decision:** I ignore the `usdprice` column.
- **Why:** the implied exchange rates jump tenfold in some rows (decimal errors). If I need dollar values, I will convert
  naira prices with a separate exchange-rate series.

## D-004: Use `actual` and `aggregate` rows together (2026-11-18, replaces my 2026-11-16 choice of actual rows only)
- **Decision:** I treat both as one price per market, month and item, and keep `priceflag` as a column.
- **Why:** in the North-East they never overlap (0 of 28,150 aggregate rows share a market, month and item with an actual
  row). Actual rows stop in 2026-04, while aggregate rows run to 2026-11 and cover twice as many markets, so "actual only"
  would drop the last 7 months and half the markets. A check fails if they ever overlap.

## D-005: Phase 1 scope (2026-11-18)
- **Decision:** Borno, Yobe and Adamawa; retail prices; 2016-01 onwards.
- **Basket:** the 25 foods with monthly prices up to 2026-11 (bananas, red and white beans, cowpeas, eggs, fish,
  groundnuts, maize flour, beef, goat meat, milk powder, millet, palm oil, vegetable oil, onions, oranges, imported and
  local rice, salt, sorghum, spinach, sugar, tomatoes, watermelons, yam). Items that stop in 2023-01, petrol (not food)
  and Maggi seasoning (starts 2025-12) stay in the clean table but not in the basket.
- **Later note:** these series turned out to have gaps (D-011), and spinach was left out of the indices (D-014).

## D-006: Units (2026-11-18)
- **Decision:** I keep the published pack price and add a price per standard unit (kg, litre or piece) to compare items.
  Each North-East retail item has exactly one pack size, so nothing changes within an item.

## D-007: Outliers are flagged, never deleted (2026-11-18)
- **Decision:** I flag a price above 5x or below 1/5 of the same item's median across markets in that month.
- **Why:** an extreme value may be a data error or a real shock. Keeping it visible lets each analysis decide.

## D-008: Price indices from matched markets (2026-11-18, replaced by D-012)
- **Decision:** each month's change for an item uses only the markets that report it in both months, and the monthly
  changes are chained into an index.
- **Why:** the number of markets reporting changes a lot (5 to 38 a month). A plain average of all markets would partly
  measure which markets reported, not how prices moved.

## D-009: Low-coverage months (2026-11-18)
- **Decision:** I flag months where fewer than 10 markets report an item.
- **Why:** some 2022 months had only 5 markets, so their figures are less reliable.

## D-010: Adamawa ends in 2025-11 (2026-11-18)
- **Decision:** I include Adamawa up to 2025-11 and note the end; state-level series are not extended.

## D-011: Basket start date and the 2022 gap (2026-11-20)
- **Found:** the basket items are not unbroken. Collection ramped up from 2016 to mid-2017, and 20 of the 25 items have
  no prices from June 2022 to January 2023. Spinach is also missing in March and April 2020.
- **Decision:** I start the basket analysis in 2017-07 and shade the 2022 gap on every chart. Outside the gap, an item may
  miss at most 2 months; more stops the run.
- **Affects:** `BASKET_START`, `KNOWN_GAP`, `MAX_MISSING_MONTHS` in `pipeline/clean_wfp.py`; `checks/check_clean.py`.
- **Later notes:** the index method in D-012 handles the gap without a bridging step, and D-017 moved the start of the
  final figures to September 2018.

## D-012: Time-dummy indices (2026-11-25, replaces D-008)
- **Decision:** for each item and area I fit log price = month effect + market effect. The basket repeats this on the item
  indices (month + item effects, equal weights). The base period was first July 2017 to June 2018 = 100 (see D-017).
- **Why:** the chained version drifted (fish 21.3x against 9.6x in plain medians). I use a base period rather than one
  month because some series have no price in July 2017.
- **Affects:** `pipeline/indices.py`, `checks/check_indices.py`. Past values can shift slightly as new months are added.

## D-013: Suspected recording errors (2026-11-25, replaced by D-016)
- **Decision:** I removed a state-item month only if (1) it jumped more than 3x and the next reading undid it, and (2) its
  median was also at least 2x beyond every other month of that series.
- **Why:** prices in Nigeria can move sharply for real reasons, so a jump alone is not proof. Of 9 candidates, 5 passed
  both tests: milk powder in Borno and Yobe (2022-05) and Borno (2025-12), and Yobe bananas and oranges (2021-05). I kept
  Borno bananas (2025-01), fish (2017-09, 2018-05) and salt (2022-05).
- **Effect:** the November 2026 basket was 351.3 with none or five removed and 351.0 with all nine (old base).

## D-014: Spinach is not in the indices (2026-11-25)
- **Decision:** I leave spinach out of the indices and keep it in the clean table, so the index basket has 24 items.
- **Why:** the typical price sits near 50 naira for most of 2017 to 2023, Borno has long gaps, and Borno prices are 5 to
  9x higher from April to November 2019 while Yobe stays at 50. The cause is not known.

## D-015: Suspect sugar and Yobe May 2021 prices kept with a warning (2026-11-25, replaced by D-016)
- **Decision:** I kept sugar (2024-10 to 2024-11, 2026-07 to 2026-09) and Yobe eggs, sugar and watermelons (2021-05) in
  the indices, and marked those months on the basket chart.
- **Why:** coverage is already thin, and it is not confirmed that these prices are errors.
- **Effect:** the index could be up to about 8% too high in the sugar months, and read 99 instead of 106 in May 2021.

## D-016: Suspected prices are shown and measured, never counted (2026-11-25, replaces D-013 and D-015)
- **Decision:** my headline figures, calculations and findings use clean prices only. Suspected prices stay in the clean
  table and appear in the reports and dashboard with the effect they would have.
- **Suspected means** any of: spinach (D-014); an outlier (D-007); the six mixed-up Yobe foods in May 2021; a state month
  that jumps more than 3x and is undone by the next reading; or a state median, a market's own price or a single price
  more than 3x away from the readings both before and after. The rules are in `pipeline/suspects.py`.
- **Why:** conclusions should rest only on prices that nothing casts doubt on, while readers can still see the rest.
  Suspected does not mean proven wrong.
- **Limits:** the latest month cannot yet be compared with later readings, and some removed prices may be real.
- **Affects:** `pipeline/suspects.py`, `indices.py`, `report_indices.py`, `report_quality.py`, `checks/check_indices.py`.

## D-017: Final figures start in September 2018 (2026-11-25)
- **Found:** in June 2018, eleven Yobe foods halve at once and stay there; both oils follow by August. Borno shows no such
  step. Before it, these 13 foods cost about 1.4 to 1.8 times Borno's price in Yobe; after it, nearly all are at or below
  Borno's. A change in the measure would explain it, but this is not confirmed. My first base year (July 2017 to June 2018)
  was affected.
- **Also found:** Yobe in October 2020 and Borno in April 2022, where the whole basket drops by over 20% and returns a
  month later.
- **Decision:** my final figures start in September 2018, with September 2018 to August 2019 = 100. Earlier prices and the
  two state months are treated as suspected and still shown (D-016).
- **Effect:** the November 2026 basket is 4.5 times the base year, not the 3.5 I first had. Yobe has now risen more than Borno.

## D-018: How I answer the three questions (2026-11-25)
- **Cost:** one pack of each of the 24 foods at a typical price from the last 12 months, carried back with the item
  indices. Months missing a food are left blank. Dearer packs weigh more than in the index.
- **Places:** each market's last 6 months against the same months a year earlier; at least 15 foods with 3 matching months
  each; 95% ranges across foods.
- **Unusual moves:** 3-month changes more than 3 robust standard deviations from usual, seen in Borno and Yobe together.
- **Affects:** `pipeline/questions.py`, `reports/findings.md`.

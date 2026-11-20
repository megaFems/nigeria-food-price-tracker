# Decisions

One entry per decision: what was decided, why, and what it affects. Newest last. "OPEN" means waiting on the owner.

## D-001: Use WFP (HDX) as the first source, downloaded by script (2026-11-16)
- **Decision:** start with the WFP "Nigeria - Food Prices" dataset from HDX.
- **Why:** open licence (CC BY-IGO), stable API, monthly updates, history back to 2002. NBS needs a login.
- **Affects:** `pipeline/ingest_wfp.py`; credit line "Source: WFP via HDX (CC BY-IGO)" on every chart.

## D-002: Scope, given WFP is not national after 2022 (DECIDED 2026-11-18: option C)
WFP covers about 13 states to 2022 but only Borno and Yobe (plus Adamawa to 2025) since 2023. Options:
- **A. National tracker:** add NBS Selected Food Price Watch (all 36 states + FCT) as the main source; WFP for long history and the North-East deep dive. Needs the owner to register on the NBS catalogue and download the files.
- **B. North-East focus:** "Food prices in Nigeria's North-East crisis states, 2016 to 2026", WFP only. Fully automatable, rich basket, strong humanitarian story; not national.
- **C. Both, staged:** build B first (automated, publishable), then add A as a second phase.
- **Decided: C.** Phase 1 is the North-East analysis on WFP data (Borno, Yobe, Adamawa). Phase 2 adds NBS
  for national coverage once the NBS files are downloaded by hand.

## D-003: Never use WFP `usdprice` (2026-11-16)
- **Decision:** ignore the `usdprice` column.
- **Why:** implied exchange rates jump tenfold in some rows (decimal errors). If USD values are needed, convert naira prices with a separate exchange-rate series.

## D-004: Use `actual` and `aggregate` rows together (2026-11-18, replaces the 2026-11-16 version)
- **Decision:** treat both as one price per market, month and item; keep `priceflag` as a column.
- **Why:** in the North-East they never overlap (0 of 28,150 aggregate rows share a market, month and item with an
  actual row). Actual rows stop in 2026-04 while aggregate rows run to 2026-11 and cover twice as many markets,
  so "actual only" would drop the last 7 months and half the markets. A check fails if they ever overlap.

## D-005: Phase 1 scope (2026-11-18)
- **Decision:** Borno, Yobe and Adamawa; retail prices; 2016-01 onwards.
- **Basket:** the 25 food items with unbroken monthly series to 2026-11 (bananas, red and white beans, cowpeas, eggs,
  fish, groundnuts, maize flour, beef, goat meat, milk powder, millet, palm oil, vegetable oil, onions, oranges,
  imported and local rice, salt, sorghum, spinach, sugar, tomatoes, watermelons, yam). Items that stop in 2023-01,
  petrol (not food) and Maggi seasoning (starts 2025-12) stay in the clean table but not in the basket.

## D-006: Units (2026-11-18)
- **Decision:** keep the published pack price, and add the price per standard unit (kg, litre or piece) for
  comparisons between items. Each North-East retail item has exactly one pack size, so within an item nothing changes.

## D-007: Outliers are flagged, never deleted (2026-11-18)
- **Decision:** flag a price above 5x or below 1/5 of the same item's median across markets in that month.
- **Why:** extreme values may be data errors or real shocks; keeping them visible lets each analysis choose.

## D-008: Price indices from matched markets (2026-11-18)
- **Decision:** each month's change for an item uses only markets that report it in both months; the monthly
  changes are chained into an index.
- **Why:** the markets reporting change a lot (5 to 38 a month). A plain average of all markets would partly
  measure which markets reported, not how prices moved.

## D-009: Low-coverage months (2026-11-18)
- **Decision:** flag months where fewer than 10 markets report an item.
- **Why:** some 2022 months had only 5 markets; their figures are less reliable.

## D-011: Basket start date and the 2022 gap (2026-11-20)
- **Found:** the basket items are not unbroken. Collection ramped up through 2016 to mid-2017, and 20 of the 25
  items have no prices from June 2022 to January 2023. Spinach is also missing in March and April 2020.
- **Decision:** basket analysis starts in 2017-07. The 2022 gap is bridged in one step (May 2022 to February 2023,
  matched markets only) and shaded on every chart. Outside the gap, an item may miss at most 2 months; more stops the run.
- **Affects:** `BASKET_START`, `KNOWN_GAP`, `MAX_MISSING_MONTHS` in `pipeline/clean_wfp.py`; `checks/check_clean.py`.

## D-010: Adamawa ends in 2025-11 (2026-11-18)
- **Decision:** include Adamawa up to 2025-11 and mark the end on charts; state-level series do not extend it.

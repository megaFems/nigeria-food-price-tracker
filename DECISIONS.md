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

## D-008: Price indices from matched markets (2026-11-18, replaced by D-012)
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

## D-012: Time-dummy indices (2026-11-25, replaces D-008)
- **Decision:** per item and area, fit log price = month effect + market effect; the basket repeats this on the item
  indices (month + item effects, equal weights). July 2017 to June 2018 = 100.
- **Why:** the chained version drifted (fish 21.3x against 9.6x in plain medians). A base year is used because some
  series have no price in July 2017.
- **Affects:** `pipeline/indices.py`, `checks/check_indices.py`. Past values can shift slightly as months are added.

## D-013: Suspected recording errors (2026-11-25, replaced by D-016)
- **Decision:** a state-item month is removed only if (1) it jumps more than 3x and the next reading undoes it, and
  (2) its median is also at least 2x beyond every other month of that series.
- **Why:** prices in Nigeria can move sharply for real reasons, so a jump alone is not proof. Of 9 candidates, 5 pass
  both tests: milk powder in Borno and Yobe (2022-05) and Borno (2025-12), Yobe bananas and oranges (2021-05). Kept:
  Borno bananas (2025-01), fish (2017-09, 2018-05), salt (2022-05).
- **Effect:** the November 2026 basket is 351.3 with none or five removed and 351.0 with all nine.

## D-014: Spinach is not in the indices (2026-11-25)
- **Decision:** left out of the indices, kept in the clean table; the index basket has 24 items.
- **Why:** the typical price sits near 50 naira for most of 2017 to 2023, Borno has long gaps, and Borno prices are 5 to
  9x higher from April to November 2019 while Yobe stays at 50. The cause is not known.

## D-015: Suspect sugar and Yobe May 2021 prices are kept with a warning (2026-11-25, replaced by D-016)
- **Decision:** keep sugar (2024-10 to 2024-11, 2026-07 to 2026-09) and Yobe eggs, sugar and watermelons (2021-05) in the
  indices; mark those months on the basket chart and explain them in the report.
- **Why:** coverage is already thin, and it is not confirmed that these prices are errors.
- **Effect:** the index may be up to about 8% too high in the sugar months, and reads 99 instead of 106 in May 2021.
  November 2026 barely changes.

## D-016: Suspected prices are shown and measured, never counted (2026-11-25, replaces D-013 and D-015)
- **Decision:** headline, calculations and findings use clean prices only. Suspected prices stay in the clean table and appear
  in the reports and charts with the percentage effect they would have.
- **Suspected means** any of: spinach (D-014); an outlier (D-007); the six mixed-up Yobe foods in May 2021; a state month that
  jumps more than 3x and is undone by the next reading (including the ones D-013 had kept); a state median, a market's own price
  or a single price more than 3x away from readings both before and after. Rules are in `pipeline/suspects.py`.
- **Why:** conclusions should rest only on prices nothing casts doubt on, while readers can still see the rest. Suspected is
  not proven wrong.
- **Limits:** the latest month cannot be compared with later readings yet. Some removed prices may be real.
- **Effect:** 2,460 of 52,314 basket prices (1,818 of them spinach). November 2026 is 350.8 clean, 350.4 with everything.
- **Affects:** `pipeline/suspects.py`, `indices.py`, `report_indices.py`, `report_quality.py`, `checks/check_indices.py`.

## D-017: Clean series starts in September 2018 (2026-11-25)
- **Found:** in June 2018 eleven Yobe foods halve at once and stay there; both oils follow by August. Borno has no such step.
  Before, these 13 foods cost about 1.4 to 1.8 times Borno's price in Yobe; after, nearly all are at or below it. A change in the
  measure would explain it, but this is not confirmed. The old base year (July 2017 to June 2018) was affected.
- **Also found:** Yobe in October 2020 and Borno in April 2022, where the whole basket drops over 20% and returns a month later.
- **Decision:** final figures start in September 2018, with September 2018 to August 2019 = 100. The two state months are
  suspected. All are still shown as suspects (D-016).
- **Effect:** the November 2026 basket is 4.5 times the base year, not 3.5 (different base). Yobe has now risen more than Borno.

## D-018: How the three questions are answered (2026-11-25)
- **Cost:** one pack of each of the 24 foods at a typical price of the last 12 months, carried back with the item indices. Months
  missing a food are blank. Dearer packs weigh more than in the index.
- **Places:** each market's last 6 months against a year earlier; at least 15 foods with 3 matching months each; 95% ranges
  across foods.
- **Unusual moves:** 3-month changes more than 3 robust standard deviations from usual, in Borno and Yobe together.
- **Affects:** `pipeline/questions.py`, `reports/findings.md`.

# Decisions

One entry per decision: what was decided, why, and what it affects. Newest last. "OPEN" means waiting on the owner.

## D-001: Use WFP (HDX) as the first source, downloaded by script (2026-11-16)
- **Decision:** start with the WFP "Nigeria - Food Prices" dataset from HDX.
- **Why:** open licence (CC BY-IGO), stable API, monthly updates, history back to 2002. NBS needs a login.
- **Affects:** `pipeline/ingest_wfp.py`; credit line "Source: WFP via HDX (CC BY-IGO)" on every chart.

## D-002: Scope, given WFP is not national after 2022 (OPEN, 2026-11-16)
WFP covers about 13 states to 2022 but only Borno and Yobe (plus Adamawa to 2025) since 2023. Options:
- **A. National tracker:** add NBS Selected Food Price Watch (all 36 states + FCT) as the main source; WFP for long history and the North-East deep dive. Needs the owner to register on the NBS catalogue and download the files.
- **B. North-East focus:** "Food prices in Nigeria's North-East crisis states, 2016 to 2026", WFP only. Fully automatable, rich basket, strong humanitarian story; not national.
- **C. Both, staged:** build B first (automated, publishable), then add A as a second phase.
- **Recommendation:** C.

## D-003: Never use WFP `usdprice` (2026-11-16)
- **Decision:** ignore the `usdprice` column.
- **Why:** implied exchange rates jump tenfold in some rows (decimal errors). If USD values are needed, convert naira prices with a separate exchange-rate series.

## D-004: Choose one `priceflag` per analysis (2026-11-16, to confirm in the cleaning step)
- **Decision:** default to `actual` market observations; treat `aggregate` rows as WFP summaries, never mixed with `actual` in the same average.
- **Why:** mixing them double-counts.

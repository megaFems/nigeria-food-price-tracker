# Data sources

Every dataset the project uses: where it comes from, its licence, how it is downloaded, and what profiling found.
Raw files live in `data/raw/` (not in git); `data/raw/manifest.json` records each download (URL, date, size, SHA-256).

## 1. WFP food prices for Nigeria (HDX): IN USE

| | |
|---|---|
| Publisher | World Food Programme, via the Humanitarian Data Exchange (HDX) |
| Dataset page | https://data.humdata.org/dataset/wfp-food-prices-for-nigeria |
| API used | `https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-nigeria` |
| Files | "Nigeria - Food Prices" (`wfp_food_prices_nga.csv`, about 11 MB), "Nigeria - Markets" (`wfp_markets_nga.csv`) |
| Licence | Creative Commons Attribution for Intergovernmental Organisations (CC BY-IGO): reuse allowed with credit |
| Sources inside it | FEWS NET via FAO (GIEWS, FPMA), SIMA Niger, WFP |
| Update frequency | Monthly (HDX says every 30 days) |
| Download script | `python pipeline/ingest_wfp.py` |
| First downloaded | 2026-11-16 (data to 2026-11-15) |

**Profile (2026-11-16, full detail in `reports/profile_wfp.md`):**
- 91,216 rows, 2002-01 to 2026-11, 14 states, 68 markets, 43 commodities. No missing values, no duplicate rows, no duplicate keys.
- **Coverage is not national.** About 13 states from 2014 to 2022 (mainly cereals, cowpeas, gari, fuel). From 2023 only Borno and Yobe (Adamawa to 2025-11). These are WFP's North-East monitoring states.
- North-East basket from 2016: about 25 retail items (rice, beans, gari, eggs, tomatoes, onions, palm and vegetable oil, beef, goat, fish, milk powder, sugar, salt, petrol, etc.).
- **Units vary within a commodity** (e.g. millet 2.6 KG, KG, 100 KG). Must convert to price per standard unit before comparing.
- **`priceflag`:** `actual` (market observation), `aggregate` (WFP-computed average), `actual,aggregate`. Using both double-counts.
- **`usdprice` has decimal errors:** implied NGN per USD jumps tenfold in some rows (e.g. 16,200 in 2014 vs about 162). Do not use `usdprice`; convert with a separate exchange-rate series if USD is needed.
- 47 prices above 10x and 33 below 1/10 of the median for the same commodity, unit, price type and year: candidates for outlier rules.

## 2. NBS Selected Food Price Watch: PLANNED (needs a login)

| | |
|---|---|
| Publisher | National Bureau of Statistics (NBS), Nigeria |
| Where | NBS microdata catalogue: https://microdata.nigerianstat.gov.ng/index.php/catalog/162 |
| Coverage | Monthly average prices of selected food items for all 36 states and the FCT |
| Access | Free, but the catalogue requires a registered account: files must be downloaded by hand and placed in `data/raw/nbs/` |
| Latest seen | Catalogue listed files to March 2026; news coverage of the April 2026 release (checked 2026-11-16) |
| Licence | To confirm from the NBS terms of use before publishing |

Why it matters: it is the only source here with all states in 2023 to 2026. See DECISIONS.md, D-002.

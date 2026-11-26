# Nigeria Food Price Tracker

A reproducible data pipeline and analysis of staple food prices in Nigeria: which items and places rose
fastest, what a basic food basket costs over time, and which price moves are unusual.

**Live dashboard:** https://ne-nigeria-food-prices.streamlit.app

**Status:** phase 1 (North-East: Borno, Yobe, Adamawa) is complete. The findings are in [reports/findings.md](reports/findings.md).
Design decisions are recorded in [DECISIONS.md](DECISIONS.md).

## Data
- **World Food Programme food prices for Nigeria**, via the Humanitarian Data Exchange (HDX), licence CC BY-IGO.
  Monthly market prices, 2002 to present. See [DATA_SOURCES.md](DATA_SOURCES.md) for coverage and caveats.
- Possible later: **NBS Selected Food Price Watch**. The tables checked so far give zone averages, not every state.

## Why the North-East and not all of Nigeria
I looked for a free source with food prices for every state, every month, up to now. I did not find one:
- **WFP (this project's source):** 14 states, but 11 stopped in January 2023; only Borno and Yobe continue.
- **NBS Selected Food Price Watch:** the tables I checked give national and zone averages and the highest and lowest
  state, from November 2024; the food list and pack sizes change between months.
- **NBS Consumer Price Index:** monthly food inflation for every state, but as rates, not prices.
- **World Bank crowdsourced prices with NBS:** all 36 states and the FCT, but 10 staples and only December 2024 to June 2025.
- **World Bank Real Time Prices:** 73 markets back to 2007, but partly modelled (estimated) prices.
- **FEWS NET:** staple prices for selected markets only.

So this project goes deep on the one area with current, detailed monthly prices. A national view is possible with the
sources above, each with the limits shown.

## Run it
```
pip install -r requirements.txt
python pipeline/ingest_wfp.py    # download the latest WFP files
python pipeline/profile_wfp.py   # write reports/profile_wfp.md
python pipeline/clean_wfp.py     # build data/processed/wfp_ne_retail_clean.parquet (stops if a check fails)
python pipeline/indices.py       # price indices
python pipeline/report_indices.py # write reports/indices_summary.md and charts
python pipeline/report_quality.py # write reports/data_quality.md
python pipeline/questions.py     # write reports/findings.md
python pipeline/export_dashboard.py  # copy the dashboard tables into dashboard/data
streamlit run dashboard/app.py   # open the dashboard
```

## Credits
Source: World Food Programme, via the Humanitarian Data Exchange (CC BY-IGO).

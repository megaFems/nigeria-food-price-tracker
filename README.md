# Nigeria Food Price Tracker

A reproducible data pipeline and analysis of staple food prices in Nigeria: which items and places rose
fastest, what a basic food basket costs over time, and which price moves are unusual.

**Status:** phase 1 (North-East: Borno, Yobe, Adamawa). Data downloaded, profiled and cleaned with checks;
price indices next.
Design decisions are recorded in [DECISIONS.md](DECISIONS.md).

## Data
- **World Food Programme food prices for Nigeria**, via the Humanitarian Data Exchange (HDX), licence CC BY-IGO.
  Monthly market prices, 2002 to present. See [DATA_SOURCES.md](DATA_SOURCES.md) for coverage and caveats.
- Planned: **NBS Selected Food Price Watch** (all states), once access is set up.

## Run it
```
pip install -r requirements.txt
python pipeline/ingest_wfp.py    # download the latest WFP files
python pipeline/profile_wfp.py   # write reports/profile_wfp.md
python pipeline/clean_wfp.py     # build data/processed/wfp_ne_retail_clean.parquet (stops if a check fails)
```

## Credits
Source: World Food Programme, via the Humanitarian Data Exchange (CC BY-IGO).

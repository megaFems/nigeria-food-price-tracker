# Nigeria Food Price Tracker

A reproducible data pipeline and analysis of staple food prices in Nigeria: which items and places rose
fastest, what a basic food basket costs over time, and which price moves are unusual.

**Status:** early. Data source checked, downloaded and profiled; cleaning and analysis next.
Design decisions are recorded in [DECISIONS.md](DECISIONS.md).

## Data
- **World Food Programme food prices for Nigeria**, via the Humanitarian Data Exchange (HDX), licence CC BY-IGO.
  Monthly market prices, 2002 to present. See [DATA_SOURCES.md](DATA_SOURCES.md) for coverage and caveats.
- Planned: **NBS Selected Food Price Watch** (all states), once access is set up.

## Run it
```
pip install -r requirements.txt
python pipeline/ingest_wfp.py
python pipeline/profile_wfp.py
```

## Credits
Source: World Food Programme, via the Humanitarian Data Exchange (CC BY-IGO).

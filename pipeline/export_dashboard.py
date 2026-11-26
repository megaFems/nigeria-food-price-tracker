"""Copy the small tables the dashboard needs into dashboard/data/, so the app runs without rebuilding the pipeline.

Usage:  python pipeline/export_dashboard.py   (run pipeline/indices.py and pipeline/questions.py first)
"""
import pathlib
import shutil

from indices import OUT_BASKET, OUT_BASKET_ALL, OUT_EFFECTS, OUT_ITEMS, OUT_ITEMS_ALL, OUT_MARKED
from questions import OUT_COST, OUT_MARKETS

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard" / "data"
KEEP = ["month", "state", "market", "commodity", "unit", "price_ngn", "suspect"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (OUT_ITEMS, OUT_ITEMS_ALL, OUT_BASKET, OUT_BASKET_ALL, OUT_EFFECTS, OUT_COST, OUT_MARKETS):
        shutil.copyfile(f, OUT / f.name)
    import pandas as pd
    pd.read_parquet(OUT_MARKED, columns=KEEP).to_parquet(OUT / "prices.parquet", index=False)
    size = sum(p.stat().st_size for p in OUT.iterdir())
    print(f"wrote {len(list(OUT.iterdir()))} files to {OUT.relative_to(ROOT)} ({size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()

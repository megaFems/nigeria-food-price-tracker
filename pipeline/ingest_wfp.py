"""Download the latest WFP "Nigeria - Food Prices" files from HDX and record exactly what was downloaded.

Each run saves dated copies in data/raw/ and appends one entry per file to data/raw/manifest.json
(source URL, HDX last-modified time, size, SHA-256, licence). If a file is identical to the last copy,
the new copy is discarded and the manifest says "unchanged".

Usage:  python pipeline/ingest_wfp.py
"""
import datetime as dt
import hashlib
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "manifest.json"

PACKAGE = "wfp-food-prices-for-nigeria"
API = f"https://data.humdata.org/api/3/action/package_show?id={PACKAGE}"
WANTED = {                       # HDX resource name -> local file stem
    "Nigeria - Food Prices": "wfp_food_prices_nga",
    "Nigeria - Markets": "wfp_markets_nga",
}
TIMEOUT_S = 120


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "nigeria-food-price-tracker/0.1"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return r.read()


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []
    meta = json.loads(fetch(API))["result"]
    today = dt.date.today().isoformat()
    found = {r["name"]: r for r in meta["resources"]}
    missing = set(WANTED) - set(found)
    if missing:
        raise SystemExit(f"HDX no longer lists these resources: {sorted(missing)}. Check {API}")

    for name, stem in WANTED.items():
        res = found[name]
        body = fetch(res["url"])
        digest = sha256(body)
        previous = [m for m in manifest if m["stem"] == stem and m["status"] != "unchanged"]
        status = "unchanged" if previous and previous[-1]["sha256"] == digest else "new"
        path = RAW / f"{stem}_{today}.csv"
        if status == "new":
            path.write_bytes(body)
        manifest.append({
            "stem": stem, "file": path.name if status == "new" else previous[-1]["file"], "status": status,
            "downloaded_at": dt.datetime.now().isoformat(timespec="seconds"),
            "source_url": res["url"], "hdx_resource_last_modified": res.get("last_modified"),
            "hdx_dataset_last_modified": meta.get("last_modified"), "dataset_date": meta.get("dataset_date"),
            "licence": meta.get("license_title"), "bytes": len(body), "sha256": digest,
        })
        print(f"{name}: {status}, {len(body):,} bytes -> {manifest[-1]['file']}")

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest: {MANIFEST.relative_to(ROOT)} ({len(manifest)} entries)")


if __name__ == "__main__":
    main()

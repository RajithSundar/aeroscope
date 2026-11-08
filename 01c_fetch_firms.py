"""
01c_fetch_firms.py
Downloads satellite fire detections (NASA FIRMS, VIIRS S-NPP 375 m) over India and its
upwind neighbourhood for the study years. These give independent evidence for the
"crop-residue / biomass smoke" signature instead of assuming it.

Needs a free FIRMS MAP_KEY: https://firms.modaps.eosdis.nasa.gov/api/map_key/
Put it in a .env file next to this script:   FIRMS_MAP_KEY=your_key_here
Without a key this script prints a warning and exits cleanly; later stages then mark
fire evidence as "not available" and carry on.

Resumable: one CSV per 5-day window in data/raw/firms/.
"""

import io
import os
import sys
import time

import pandas as pd
import requests

from aeroscope_core.config import FIRE_BBOX, FIRMS_DIR, YEARS, load_dotenv

API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{bbox}/{days}/{date}"
# Standard-processing (science quality) archive first; near-real-time fills recent gaps.
SOURCES = ["VIIRS_SNPP_SP", "VIIRS_SNPP_NRT"]
DAYS_PER_CALL = 5  # FIRMS area API accepts 1..5 days per request
KEEP = ["latitude", "longitude", "acq_date", "frp", "confidence", "daynight"]


def fetch_window(key: str, start: pd.Timestamp, days: int) -> pd.DataFrame:
    bbox = ",".join(map(str, FIRE_BBOX))
    for source in SOURCES:
        url = API.format(key=key, source=source, bbox=bbox, days=days, date=start.strftime("%Y-%m-%d"))
        for attempt in range(4):
            resp = requests.get(url, timeout=120)
            if resp.status_code == 429:
                time.sleep(60)
                continue
            break
        if resp.status_code != 200:
            raise RuntimeError(f"FIRMS HTTP {resp.status_code}: {resp.text[:200]}")
        text = resp.text.strip()
        if text.lower().startswith("invalid"):
            raise RuntimeError(f"FIRMS rejected the request: {text[:200]}")
        df = pd.read_csv(io.StringIO(text)) if text else pd.DataFrame()
        if len(df):
            df = df[[c for c in KEEP if c in df.columns]]
            # VIIRS confidence: l(ow) / n(ominal) / h(igh). Drop low-confidence detections.
            df = df[df["confidence"].astype(str).str.lower() != "l"]
            df["source"] = source
            return df
    return pd.DataFrame(columns=KEEP + ["source"])


def main():
    load_dotenv()
    key = os.environ.get("FIRMS_MAP_KEY", "").strip()
    if not key:
        print("FIRMS_MAP_KEY not set - skipping fire download.\n"
              "Get a free key at https://firms.modaps.eosdis.nasa.gov/api/map_key/ and add\n"
              "FIRMS_MAP_KEY=... to .env, then re-run. The pipeline still works without it.")
        return
    FIRMS_DIR.mkdir(parents=True, exist_ok=True)
    starts = pd.date_range(f"{YEARS[0]}-01-01", f"{YEARS[-1]}-12-31", freq=f"{DAYS_PER_CALL}D")
    for i, start in enumerate(starts, 1):
        out = FIRMS_DIR / f"fires_{start:%Y%m%d}.csv"
        if out.exists():
            continue
        end = min(start + pd.Timedelta(days=DAYS_PER_CALL - 1), pd.Timestamp(f"{YEARS[-1]}-12-31"))
        days = (end - start).days + 1
        try:
            df = fetch_window(key, start, days)
        except RuntimeError as exc:
            print(f"  stopped at {start:%Y-%m-%d}: {exc}")
            sys.exit(2)
        df.to_csv(out, index=False)
        print(f"  [{i}/{len(starts)}] {start:%Y-%m-%d} +{days}d: {len(df):,} detections", flush=True)
        time.sleep(1.0)
    print("FIRMS download complete.")


if __name__ == "__main__":
    main()

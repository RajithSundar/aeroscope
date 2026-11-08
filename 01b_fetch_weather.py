"""
01b_fetch_weather.py
Downloads ERA5 reanalysis weather (Open-Meteo Historical Weather API, no key) for each
CAMS grid cell, for the smoke and winter seasons only (Oct-Feb), which is where we need it:

  * wind direction -> which fires are UPWIND of a city (smoke attribution)
  * wind speed x boundary-layer height = ventilation coefficient -> stagnant winter air

Restricting to Oct-Feb keeps the run inside Open-Meteo's free daily quota.
Resumable: one CSV per grid cell in data/raw/weather/.
"""

import sys

import numpy as np
import pandas as pd

from aeroscope_core.config import GRID_CELLS_CSV, TIMEZONE, WEATHER_DIR, YEARS
from aeroscope_core.http import DailyLimitReached, Pacer, get_json, open_meteo_weight

API = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARS = ["wind_speed_10m", "wind_direction_10m", "boundary_layer_height"]
BATCH = 5


def season_windows():
    """Oct-Feb windows covering every smoke/winter season in the study years."""
    first, last = YEARS[0], YEARS[-1]
    windows = [(f"{first}-01-01", f"{first}-02-28")]
    for y in range(first, last):
        windows.append((f"{y}-10-01", f"{y + 1}-02-{29 if (y + 1) % 4 == 0 else 28}"))
    windows.append((f"{last}-10-01", f"{last}-12-31"))
    return windows


def hourly_to_daily(hourly: dict) -> pd.DataFrame:
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"])
    df["date"] = df["time"].dt.date
    speed_ms = df["wind_speed_10m"] / 3.6
    rad = np.deg2rad(df["wind_direction_10m"])
    # Direction the wind blows FROM, averaged as a vector so 350 and 10 degrees average to 0.
    df["u"] = -speed_ms * np.sin(rad)
    df["v"] = -speed_ms * np.cos(rad)
    df["speed_ms"] = speed_ms
    g = df.groupby("date")
    u, v = g["u"].mean(), g["v"].mean()
    wind_from = (np.rad2deg(np.arctan2(-u, -v)) + 360) % 360
    daily = pd.DataFrame({
        "wind_speed_ms": g["speed_ms"].mean(),
        "wind_from_deg": wind_from,
        "wind_steadiness": np.hypot(u, v) / g["speed_ms"].mean().replace(0, np.nan),
        "blh_max_m": g["boundary_layer_height"].max(),
    })
    # Ventilation coefficient (m2/s): afternoon mixing height x mean wind. < 2000 = poor dispersion.
    daily["ventilation_coef"] = daily["blh_max_m"] * daily["wind_speed_ms"]
    return daily.reset_index().round(3)


def main():
    WEATHER_DIR.mkdir(parents=True, exist_ok=True)
    cells = pd.read_csv(GRID_CELLS_CSV).drop_duplicates("cell_id")
    todo = cells[[not (WEATHER_DIR / f"{c}.csv").exists() for c in cells["cell_id"]]]
    windows = season_windows()
    print(f"{len(cells)} grid cells, {len(todo)} to download; windows: {windows}")
    pacer = Pacer()
    try:
        for start in range(0, len(todo), BATCH):
            chunk = todo.iloc[start:start + BATCH]
            frames = {c: [] for c in chunk["cell_id"]}
            for w_start, w_end in windows:
                n_days = (pd.Timestamp(w_end) - pd.Timestamp(w_start)).days + 1
                pacer.wait(open_meteo_weight(len(chunk), n_days, len(HOURLY_VARS)))
                data = get_json(API, {
                    "latitude": ",".join(map(str, chunk["grid_lat"])),
                    "longitude": ",".join(map(str, chunk["grid_lon"])),
                    "hourly": ",".join(HOURLY_VARS),
                    "start_date": w_start, "end_date": w_end, "timezone": TIMEZONE,
                    "wind_speed_unit": "kmh",
                })
                data = data if isinstance(data, list) else [data]
                for cell_id, loc in zip(chunk["cell_id"], data):
                    frames[cell_id].append(hourly_to_daily(loc["hourly"]))
            for cell_id, parts in frames.items():
                pd.concat(parts).to_csv(WEATHER_DIR / f"{cell_id}.csv", index=False)
            print(f"  [{len(cells) - len(todo) + start + len(chunk)}/{len(cells)}] weather saved", flush=True)
    except DailyLimitReached as exc:
        print(f"\nOpen-Meteo daily quota reached ({exc}). Progress saved - re-run tomorrow.")
        sys.exit(2)
    print("Weather download complete.")


if __name__ == "__main__":
    main()

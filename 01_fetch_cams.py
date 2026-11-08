"""
01_fetch_cams.py
Downloads real daily air-quality data for every NCAP city from the Copernicus Atmosphere
Monitoring Service (CAMS) global model, served free (no key) by the Open-Meteo Air Quality API.

What it fetches (hourly, aggregated to Asia/Kolkata calendar days):
  PM2.5, PM10, CO, NO2, SO2, O3, aerosol optical depth (550 nm) and near-surface dust.

Important: CAMS is a ~40 km atmospheric model that assimilates satellite aerosol data.
It is NOT a ground-monitor measurement. Several nearby NCAP cities fall in the same grid
cell and therefore share identical data; this script records that mapping in
data/raw/grid_cells.csv so later stages can de-duplicate.

Resumable: one CSV per grid cell is cached in data/raw/cams/. If the free daily quota runs
out, just re-run tomorrow and it continues where it stopped.
"""

import sys

import pandas as pd

from aeroscope_core.cities import cell_id_for, load_cities
from aeroscope_core.config import CAMS_DIR, END_DATE, GRID_CELLS_CSV, START_DATE, TIMEZONE
from aeroscope_core.http import DailyLimitReached, Pacer, get_json, open_meteo_weight

API = "https://air-quality-api.open-meteo.com/v1/air-quality"
HOURLY_VARS = [
    "pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide",
    "sulphur_dioxide", "ozone", "aerosol_optical_depth", "dust",
]
BATCH = 5


def resolve_grid_cells(cities: pd.DataFrame, pacer: Pacer) -> pd.DataFrame:
    """Ask the API for one day per city to learn which model grid cell each city snaps to."""
    if GRID_CELLS_CSV.exists():
        cells = pd.read_csv(GRID_CELLS_CSV)
        if set(cells["city_id"]) == set(cities["city_id"]):
            return cells
    rows = []
    for start in range(0, len(cities), 50):
        chunk = cities.iloc[start:start + 50]
        pacer.wait(open_meteo_weight(len(chunk), 1, 1))
        data = get_json(API, {
            "latitude": ",".join(map(str, chunk["lat"])),
            "longitude": ",".join(map(str, chunk["lon"])),
            "hourly": "pm2_5", "start_date": START_DATE, "end_date": START_DATE, "timezone": TIMEZONE,
        })
        data = data if isinstance(data, list) else [data]
        for (_, city), loc in zip(chunk.iterrows(), data):
            rows.append({
                "city_id": city["city_id"],
                "grid_lat": round(loc["latitude"], 4),
                "grid_lon": round(loc["longitude"], 4),
                "cell_id": cell_id_for(loc["latitude"], loc["longitude"]),
            })
    cells = pd.DataFrame(rows)
    GRID_CELLS_CSV.parent.mkdir(parents=True, exist_ok=True)
    cells.to_csv(GRID_CELLS_CSV, index=False)
    return cells


def hourly_to_daily(hourly: dict) -> pd.DataFrame:
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"])
    df["date"] = df["time"].dt.date
    g = df.groupby("date")
    daily = pd.DataFrame({
        "pm2_5_mean": g["pm2_5"].mean(),
        "pm2_5_max": g["pm2_5"].max(),
        "pm10_mean": g["pm10"].mean(),
        "co_mean": g["carbon_monoxide"].mean(),
        "no2_mean": g["nitrogen_dioxide"].mean(),
        "so2_mean": g["sulphur_dioxide"].mean(),
        "o3_mean": g["ozone"].mean(),
        "o3_max": g["ozone"].max(),
        "aod_mean": g["aerosol_optical_depth"].mean(),
        "aod_max": g["aerosol_optical_depth"].max(),
        "dust_mean": g["dust"].mean(),
        "hours_reported": g["pm2_5"].count(),
    }).reset_index()
    return daily.round(4)


def main():
    CAMS_DIR.mkdir(parents=True, exist_ok=True)
    pacer = Pacer()
    cities = load_cities()
    print(f"Resolving CAMS grid cells for {len(cities)} NCAP cities...")
    cells = resolve_grid_cells(cities, pacer)
    unique = cells.drop_duplicates("cell_id")[["cell_id", "grid_lat", "grid_lon"]]
    print(f"  {len(cities)} cities map to {len(unique)} distinct model grid cells")

    todo = unique[[not (CAMS_DIR / f"{c}.csv").exists() for c in unique["cell_id"]]]
    print(f"  {len(unique) - len(todo)} cells cached, {len(todo)} to download ({START_DATE} to {END_DATE})")
    n_days = (pd.Timestamp(END_DATE) - pd.Timestamp(START_DATE)).days + 1

    try:
        for start in range(0, len(todo), BATCH):
            chunk = todo.iloc[start:start + BATCH]
            pacer.wait(open_meteo_weight(len(chunk), n_days, len(HOURLY_VARS)))
            data = get_json(API, {
                "latitude": ",".join(map(str, chunk["grid_lat"])),
                "longitude": ",".join(map(str, chunk["grid_lon"])),
                "hourly": ",".join(HOURLY_VARS),
                "start_date": START_DATE, "end_date": END_DATE, "timezone": TIMEZONE,
            })
            data = data if isinstance(data, list) else [data]
            for (_, cell), loc in zip(chunk.iterrows(), data):
                daily = hourly_to_daily(loc["hourly"])
                daily.to_csv(CAMS_DIR / f"{cell['cell_id']}.csv", index=False)
            done = len(unique) - len(todo) + start + len(chunk)
            print(f"  [{done}/{len(unique)}] saved cells {', '.join(chunk['cell_id'])}", flush=True)
    except DailyLimitReached as exc:
        print(f"\nOpen-Meteo daily quota reached ({exc}).\nProgress is saved - re-run this script tomorrow to finish.")
        sys.exit(2)

    print("CAMS download complete.")


if __name__ == "__main__":
    main()

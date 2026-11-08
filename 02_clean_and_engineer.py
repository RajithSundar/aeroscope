"""
02_clean_and_engineer.py
Quality-checks the CAMS daily series for each NCAP city, adds the CPCB particulate AQI,
links in fire detections (FIRMS) and ventilation (ERA5) where available, and builds:

  data/processed/daily_cleaned.csv             city x day, pollutants + particulate AQI
  data/processed/city_features.csv             city-level seasonal/source features (all years pooled)
  data/processed/city_features_by_year.csv     the same features per calendar year (for stability tests)
  data/processed/monthly_profile.csv           city x month climatology + drivers (powers the calendar)
  data/processed/cleaning_audit_report.json    what the QC step changed

Clustering features use CAMS pollutant data only. Fire and ventilation features are kept OUT
of clustering so they can serve as independent evidence when naming and validating clusters.
"""

import glob
import json

import numpy as np
import pandas as pd

from aeroscope_core import aqi as aqi_lib
from aeroscope_core.cities import load_city_cells
from aeroscope_core.config import (CAMS_DIR, FIRMS_DIR, NAAQS_PM25_24H, PROCESSED_DIR, WEATHER_DIR, YEARS)
from aeroscope_core.geo import haversine_km, is_upwind

POLLUTANT_BOUNDS = {
    "aod_mean": (0.0, 5.0),
    "aod_max": (0.0, 6.0),
    "dust_mean": (0.0, 3000.0),
    "pm2_5_mean": (0.0, 1000.0),
    "pm2_5_max": (0.0, 1500.0),
    "pm10_mean": (0.0, 2000.0),
    "co_mean": (0.0, 20000.0),
    "no2_mean": (0.0, 500.0),
    "so2_mean": (0.0, 600.0),
    "o3_mean": (0.0, 400.0),
}
FIRE_RADIUS_KM = 300.0
POOR_VENTILATION = 2000.0  # m2/s
SEASONS = ["winter_djf", "premonsoon_mam", "monsoon_jjas", "postmonsoon_on"]


def assign_imd_season(month: int) -> str:
    """India Meteorological Department seasons."""
    if month in (12, 1, 2):
        return "winter_djf"
    if month in (3, 4, 5):
        return "premonsoon_mam"
    if month in (6, 7, 8, 9):
        return "monsoon_jjas"
    return "postmonsoon_on"


# ----------------------------------------------------------------------------- loading
def load_cams(city_cells: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for _, c in city_cells.iterrows():
        path = CAMS_DIR / f"{c['cell_id']}.csv"
        if not path.exists():
            print(f"  ! no CAMS data for {c['city']} ({c['cell_id']}) - skipped; re-run 01_fetch_cams.py")
            continue
        df = pd.read_csv(path)
        df.insert(0, "city_id", c["city_id"])
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_weather(city_cells: pd.DataFrame) -> pd.DataFrame | None:
    frames = []
    for _, c in city_cells.iterrows():
        path = WEATHER_DIR / f"{c['cell_id']}.csv"
        if path.exists():
            df = pd.read_csv(path)
            df.insert(0, "city_id", c["city_id"])
            frames.append(df)
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_fires() -> pd.DataFrame | None:
    files = sorted(glob.glob(str(FIRMS_DIR / "fires_*.csv")))
    if not files:
        return None
    df = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    if df.empty:
        return None
    df["acq_date"] = pd.to_datetime(df["acq_date"])
    return df


# ----------------------------------------------------------------------------- cleaning
def clean_daily(df: pd.DataFrame):
    df = df.sort_values(["city_id", "date"]).reset_index(drop=True)
    cols = [c for c in POLLUTANT_BOUNDS if c in df.columns]
    audit = {
        "data_source": "CAMS via Open-Meteo",
        "initial_rows": int(len(df)),
        "cities": int(df["city_id"].nunique()),
        "date_range": [str(df["date"].min().date()), str(df["date"].max().date())],
        "missing_before": {c: int(df[c].isna().sum()) for c in cols},
        "out_of_bounds_removed": {},
        "incomplete_days_removed": int((df["hours_reported"] < 18).sum()) if "hours_reported" in df else 0,
    }
    if "hours_reported" in df:
        df.loc[df["hours_reported"] < 18, cols] = np.nan
    for col in cols:
        lo, hi = POLLUTANT_BOUNDS[col]
        bad = (df[col] < lo) | (df[col] > hi)
        audit["out_of_bounds_removed"][col] = int(bad.sum())
        df.loc[bad, col] = np.nan
    # Short gaps (<= 3 days) are interpolated within each city; longer gaps stay missing.
    df[cols] = df.groupby("city_id", group_keys=False)[cols].apply(
        lambda g: g.interpolate(method="linear", limit=3, limit_area="inside"))
    bad_pm = df["pm2_5_mean"] > df["pm10_mean"]
    audit["pm25_exceeding_pm10"] = int(bad_pm.sum())
    df.loc[bad_pm, "pm10_mean"] = df.loc[bad_pm, "pm2_5_mean"]
    audit["missing_after"] = {c: int(df[c].isna().sum()) for c in cols}

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["season"] = df["month"].map(assign_imd_season)
    df["aqi_pm"] = aqi_lib.particulate_aqi(df["pm2_5_mean"], df["pm10_mean"]).round(0)
    df["aqi_category"] = aqi_lib.category(df["aqi_pm"])
    df["exceeds_naaqs_pm25"] = df["pm2_5_mean"] > NAAQS_PM25_24H
    return df, audit


# ----------------------------------------------------------------------------- fire + weather
def attach_fire_counts(daily: pd.DataFrame, cities: pd.DataFrame, fires: pd.DataFrame | None,
                       weather: pd.DataFrame | None) -> pd.DataFrame:
    """Adds per city-day: fires within 300 km, and fires within 300 km in the upwind sector."""
    daily = daily.copy()
    if weather is not None:
        daily = daily.merge(weather, on=["city_id", "date"], how="left")
    else:
        for col in ("wind_speed_ms", "wind_from_deg", "wind_steadiness", "blh_max_m", "ventilation_coef"):
            daily[col] = np.nan
    daily["fires_300km"] = np.nan
    daily["fires_upwind_300km"] = np.nan
    if fires is None:
        return daily

    coords = cities.set_index("city_id")[["lat", "lon"]]
    ids = coords.index.to_numpy()
    clat, clon = coords["lat"].to_numpy()[:, None], coords["lon"].to_numpy()[:, None]
    wind = daily.pivot_table(index="date", columns="city_id", values="wind_from_deg") if weather is not None else None

    records = []
    for date, grp in fires.groupby("acq_date"):
        flat, flon = grp["latitude"].to_numpy()[None, :], grp["longitude"].to_numpy()[None, :]
        near = haversine_km(clat, clon, flat, flon) <= FIRE_RADIUS_KM
        total = near.sum(axis=1)
        if wind is not None and date in wind.index:
            wdir = wind.loc[date].reindex(ids).to_numpy()[:, None]
            up = near & is_upwind(clat, clon, flat, flon, wdir)
            upwind = np.where(np.isnan(wdir[:, 0]), np.nan, up.sum(axis=1))
        else:
            upwind = np.full(len(ids), np.nan)
        records.append(pd.DataFrame({"city_id": ids, "date": date, "f_all": total, "f_up": upwind}))
    counts = pd.concat(records, ignore_index=True)
    daily = daily.merge(counts, on=["city_id", "date"], how="left")
    # Days with no detections in the file are genuine zeros (the whole period was downloaded).
    daily["fires_300km"] = daily["f_all"].fillna(0.0)
    has_wind = daily["wind_from_deg"].notna()
    daily["fires_upwind_300km"] = np.where(has_wind, daily["f_up"].fillna(0.0), np.nan)
    return daily.drop(columns=["f_all", "f_up"])


# ----------------------------------------------------------------------------- features
def _features_for(df: pd.DataFrame) -> dict:
    """Feature vector for one city over whatever period `df` covers."""
    s = df.groupby("season")
    seasonal = s[["pm2_5_mean", "pm10_mean", "co_mean", "dust_mean", "aod_mean"]].mean()
    seasonal = seasonal.reindex(SEASONS)
    ann = df[["pm2_5_mean", "pm10_mean", "co_mean", "no2_mean", "so2_mean", "aod_mean", "dust_mean"]].mean()
    monthly_pm25 = df.groupby("month")["pm2_5_mean"].mean()
    pm25_season_sum = seasonal["pm2_5_mean"].sum()
    n_years = max(1, df["year"].nunique())

    f = {
        "annual_pm25_mean": ann["pm2_5_mean"],
        "annual_pm10_mean": ann["pm10_mean"],
        "annual_aod_mean": ann["aod_mean"],
        "annual_no2_mean": ann["no2_mean"],
        "annual_so2_mean": ann["so2_mean"],
        "annual_co_mean": ann["co_mean"],
        "annual_dust_mean": ann["dust_mean"],
        "naaqs_exceedance_days_per_year": df["exceeds_naaqs_pm25"].sum() / n_years,
        "peak_month": int(monthly_pm25.idxmax()),
        "cleanest_month": int(monthly_pm25.idxmin()),
    }
    for season in SEASONS:
        f[f"pm25_{season}"] = seasonal.loc[season, "pm2_5_mean"]
        f[f"{season.split('_')[0]}_pm25_share"] = seasonal.loc[season, "pm2_5_mean"] / pm25_season_sum
    f["postmonsoon_smoke_spike"] = (
        (seasonal.loc["postmonsoon_on", "pm2_5_mean"] / ann["pm2_5_mean"])
        * (seasonal.loc["postmonsoon_on", "co_mean"] / ann["co_mean"]))
    f["winter_inversion_ratio"] = seasonal.loc["winter_djf", "pm2_5_mean"] / ann["pm2_5_mean"]
    f["premonsoon_dust_index"] = seasonal.loc["premonsoon_mam", "dust_mean"] / (ann["dust_mean"] + 1.0)
    # CAMS "dust" covers all dust sizes (up to ~20 um), so it is not a fraction of PM10:
    # use the absolute Mar-May dust load instead of a ratio.
    f["dust_mam_mean"] = seasonal.loc["premonsoon_mam", "dust_mean"]
    f["coarse_fraction"] = float(np.clip(1 - ann["pm2_5_mean"] / ann["pm10_mean"], 0, 1))
    f["so2_to_no2_ratio"] = ann["so2_mean"] / (ann["no2_mean"] + 0.5)
    f["pm25_seasonal_cv"] = monthly_pm25.std() / monthly_pm25.mean()
    f["pm25_peak_to_mean"] = df["pm2_5_mean"].quantile(0.95) / ann["pm2_5_mean"]

    # External evidence (not used for clustering)
    on = df[df["month"].isin([10, 11])]
    djf = df[df["month"].isin([12, 1, 2])]
    f["fires_300km_on_daily"] = on["fires_300km"].mean() if on["fires_300km"].notna().any() else np.nan
    f["upwind_fires_on_daily"] = on["fires_upwind_300km"].mean() if on["fires_upwind_300km"].notna().any() else np.nan
    f["fire_pm25_lag_corr"] = _fire_lag_corr(on)
    vc = djf["ventilation_coef"]
    f["ventilation_djf_median"] = vc.median() if vc.notna().any() else np.nan
    f["poor_ventilation_days_djf"] = ((vc < POOR_VENTILATION).sum() / n_years) if vc.notna().any() else np.nan
    return f


def _fire_lag_corr(on: pd.DataFrame) -> float:
    """Best Spearman correlation between upwind (or nearby) fire counts and PM2.5 0-3 days later."""
    col = "fires_upwind_300km" if on["fires_upwind_300km"].notna().sum() > 30 else "fires_300km"
    if on[col].notna().sum() < 30 or on[col].sum() == 0:
        return np.nan
    best = np.nan
    s = on.sort_values("date").set_index("date")
    for lag in range(0, 4):
        pm_later = s["pm2_5_mean"].shift(-lag, freq="D").reindex(s.index)
        r = s[col].corr(pm_later, method="spearman")
        if pd.notna(r) and (np.isnan(best) or r > best):
            best = r
    return best


def engineer_features(daily: pd.DataFrame, cities: pd.DataFrame):
    meta = cities.set_index("city_id")[["city", "state", "lat", "lon", "list_status"]]
    pooled = pd.DataFrame({cid: _features_for(g) for cid, g in daily.groupby("city_id")}).T
    pooled = meta.join(pooled, how="inner")
    by_year = []
    for (cid, year), g in daily.groupby(["city_id", "year"]):
        row = _features_for(g)
        row.update({"city_id": cid, "year": year})
        by_year.append(row)
    by_year = pd.DataFrame(by_year)
    pooled.index.name = "city_id"
    return pooled.reset_index(), by_year


def monthly_profile(daily: pd.DataFrame) -> pd.DataFrame:
    """City x month climatology used by the planner calendar."""
    g = daily.groupby(["city_id", "month"])
    prof = pd.DataFrame({
        "pm25_median": g["pm2_5_mean"].median(),
        "pm25_p25": g["pm2_5_mean"].quantile(0.25),
        "pm25_p75": g["pm2_5_mean"].quantile(0.75),
        "pm25_mean": g["pm2_5_mean"].mean(),
        "pm10_mean": g["pm10_mean"].mean(),
        "dust_mean": g["dust_mean"].mean(),
        "co_mean": g["co_mean"].mean(),
        "no2_mean": g["no2_mean"].mean(),
        "so2_mean": g["so2_mean"].mean(),
        "aod_mean": g["aod_mean"].mean(),
        "aqi_median": g["aqi_pm"].median(),
        "exceed_days_per_year": g["exceeds_naaqs_pm25"].sum() / daily["year"].nunique(),
        "fires_300km_daily": g["fires_300km"].mean(),
        "upwind_fires_daily": g["fires_upwind_300km"].mean(),
        "ventilation_median": g["ventilation_coef"].median(),
    }).reset_index()
    prof["aqi_category"] = aqi_lib.category(prof["aqi_median"])
    ann = daily.groupby("city_id")[["pm2_5_mean", "co_mean", "so2_mean"]].mean()
    prof = prof.merge(ann.add_prefix("annual_"), left_on="city_id", right_index=True)
    prof["pm25_vs_annual"] = prof["pm25_mean"] / prof["annual_pm2_5_mean"]
    prof["co_vs_annual"] = prof["co_mean"] / prof["annual_co_mean"]
    return prof.drop(columns=[c for c in prof.columns if c.startswith("annual_")]).round(4)


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    city_cells = load_city_cells()
    print("Loading CAMS daily series...")
    raw = load_cams(city_cells)
    weather = load_weather(city_cells)
    fires = load_fires()
    print(f"  weather cells: {0 if weather is None else weather['city_id'].nunique()}, "
          f"fire detections: {0 if fires is None else len(fires):,}")

    print("Quality checks + particulate AQI...")
    daily, audit = clean_daily(raw)
    daily = attach_fire_counts(daily, city_cells, fires, weather)
    audit["weather_available"] = weather is not None
    audit["fire_data_available"] = fires is not None
    audit["fire_detections"] = 0 if fires is None else int(len(fires))

    print("Engineering city features (pooled + per year)...")
    feats, feats_year = engineer_features(daily, city_cells)
    prof = monthly_profile(daily)

    daily.to_csv(PROCESSED_DIR / "daily_cleaned.csv", index=False)
    feats.to_csv(PROCESSED_DIR / "city_features.csv", index=False)
    feats_year.to_csv(PROCESSED_DIR / "city_features_by_year.csv", index=False)
    prof.to_csv(PROCESSED_DIR / "monthly_profile.csv", index=False)
    audit["feature_columns"] = int(feats.shape[1])
    with open(PROCESSED_DIR / "cleaning_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)

    print(f"  {len(daily):,} city-days, {len(feats)} cities, {feats.shape[1]} feature columns")
    print(f"  years present: {sorted(daily['year'].unique())} (expected {list(YEARS)})")
    print(f"  out-of-bounds removed: {sum(audit['out_of_bounds_removed'].values())}, "
          f"missing after: {sum(audit['missing_after'].values())}")


if __name__ == "__main__":
    main()

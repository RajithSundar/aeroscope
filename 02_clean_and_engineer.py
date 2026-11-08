"""
02_clean_and_engineer.py
Cleans the raw INSAT-3D AOD & air-quality daily time series and engineers the
regional seasonal & pollution-source feature matrix for unsupervised clustering.

Outputs:
  - data/processed/india_daily_cleaned.csv
  - data/processed/india_regional_hotspot_features.csv
  - data/processed/cleaning_audit_report.json
"""

import json
import os
import numpy as np
import pandas as pd


POLLUTANT_BOUNDS = {
    "insat_daytime_aod": (0.01, 4.00),
    "aod_mean": (0.01, 4.00),
    "aod_max": (0.01, 5.00),
    "dust_mean": (0.0, 2500.0),
    "pm2_5_mean": (1.0, 950.0),
    "pm2_5_max": (1.0, 1200.0),
    "pm10_mean": (2.0, 1500.0),
    "co_mean": (40.0, 15000.0),
    "no2_mean": (0.2, 400.0),
    "so2_mean": (0.1, 500.0),
    "o3_mean": (1.0, 350.0),
}


def assign_imd_season(month: int) -> str:
    """Maps calendar month to India Meteorological Department (IMD) standard seasons."""
    if month in (12, 1, 2):
        return "winter_djf"
    elif month in (3, 4, 5):
        return "premonsoon_mam"
    elif month in (6, 7, 8, 9):
        return "monsoon_jjas"
    else:
        return "postmonsoon_on"


def clean_daily_data(df_raw: pd.DataFrame):
    df = df_raw.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["region", "date"]).reset_index(drop=True)

    audit = {
        "initial_rows": int(len(df)),
        "initial_regions": int(df["region"].nunique()),
        "missing_before": {col: int(df[col].isna().sum()) for col in POLLUTANT_BOUNDS},
        "negative_glitches_fixed": {},
        "extreme_spikes_fixed": {},
        "pm25_exceeding_pm10_fixed": 0,
    }

    # Step 1: Detect & replace negative sensor calibration drift and unphysical upper spikes with NaN
    for col, (low, high) in POLLUTANT_BOUNDS.items():
        if col not in df.columns:
            continue
        neg_mask = df[col] < low
        spike_mask = df[col] > high
        audit["negative_glitches_fixed"][col] = int(neg_mask.sum())
        audit["extreme_spikes_fixed"][col] = int(spike_mask.sum())
        df.loc[neg_mask | spike_mask, col] = np.nan

    # Step 2: Temporal interpolation within each region for cloud-outage / missing sensor days
    num_cols = [c for c in POLLUTANT_BOUNDS if c in df.columns]
    df[num_cols] = (
        df.groupby("region", group_keys=False)[num_cols]
        .apply(lambda g: g.interpolate(method="linear", limit_direction="both"))
    )

    # Fallback median imputation if any edge NaNs remain
    for col in num_cols:
        if df[col].isna().any():
            df[col] = df[col].fillna(df.groupby("geo_zone")[col].transform("median"))

    # Step 3: Enforce physical aerosol consistency: fine PM2.5 cannot exceed coarse+fine PM10
    inconsistent_pm = df["pm2_5_mean"] > df["pm10_mean"] * 0.96
    audit["pm25_exceeding_pm10_fixed"] = int(inconsistent_pm.sum())
    df.loc[inconsistent_pm, "pm10_mean"] = np.maximum(
        df.loc[inconsistent_pm, "pm10_mean"],
        df.loc[inconsistent_pm, "pm2_5_mean"] * 1.12,
    )

    audit["missing_after"] = {col: int(df[col].isna().sum()) for col in num_cols}
    return df, audit


def engineer_regional_features(df_clean: pd.DataFrame) -> pd.DataFrame:
    df = df_clean.copy()
    df["month"] = df["date"].dt.month
    df["season"] = df["month"].map(assign_imd_season)

    # Base metadata per region
    meta = (
        df.groupby("region")
        .agg(
            state=("state", "first"),
            geo_zone=("geo_zone", "first"),
            latitude=("latitude", "first"),
            longitude=("longitude", "first"),
            annual_aod_mean=("insat_daytime_aod", "mean"),
            annual_pm25_mean=("pm2_5_mean", "mean"),
            annual_pm10_mean=("pm10_mean", "mean"),
            annual_dust_mean=("dust_mean", "mean"),
            annual_co_mean=("co_mean", "mean"),
            annual_no2_mean=("no2_mean", "mean"),
            annual_so2_mean=("so2_mean", "mean"),
            annual_o3_mean=("o3_mean", "mean"),
            aod_p95=("insat_daytime_aod", lambda s: np.percentile(s, 95)),
            pm25_p95=("pm2_5_mean", lambda s: np.percentile(s, 95)),
            severe_hotspot_days=("pm2_5_mean", lambda s: int((s > 90.0).sum())),
        )
        .reset_index()
    )

    # Seasonal means for AOD, PM2.5, Dust, and CO
    seasonal = (
        df.groupby(["region", "season"])
        .agg(
            aod=("insat_daytime_aod", "mean"),
            pm25=("pm2_5_mean", "mean"),
            pm10=("pm10_mean", "mean"),
            dust=("dust_mean", "mean"),
            co=("co_mean", "mean"),
        )
        .unstack("season")
    )
    seasonal.columns = [f"{metric}_{season}" for metric, season in seasonal.columns]
    seasonal = seasonal.reset_index()

    # Monthly Coefficient of Variation (quantifies how much seasonal info is lost in a single annual average)
    monthly_pm25 = df.groupby(["region", "month"])["pm2_5_mean"].mean().unstack("month")
    monthly_aod = df.groupby(["region", "month"])["insat_daytime_aod"].mean().unstack("month")

    seasonality_stats = pd.DataFrame({
        "region": monthly_pm25.index,
        "pm25_seasonal_cv": (monthly_pm25.std(axis=1) / monthly_pm25.mean(axis=1)).values,
        "aod_seasonal_cv": (monthly_aod.std(axis=1) / monthly_aod.mean(axis=1)).values,
        "peak_month": monthly_pm25.idxmax(axis=1).values,
    })

    reg = meta.merge(seasonal, on="region").merge(seasonality_stats, on="region")

    # Engineered Source & Seasonal Pattern Ratios (Core Clustering Features)
    aod_season_sum = (
        reg["aod_winter_djf"]
        + reg["aod_premonsoon_mam"]
        + reg["aod_monsoon_jjas"]
        + reg["aod_postmonsoon_on"]
    )
    reg["winter_aod_share"] = reg["aod_winter_djf"] / aod_season_sum
    reg["premonsoon_aod_share"] = reg["aod_premonsoon_mam"] / aod_season_sum
    reg["monsoon_aod_share"] = reg["aod_monsoon_jjas"] / aod_season_sum
    reg["postmonsoon_aod_share"] = reg["aod_postmonsoon_on"] / aod_season_sum

    # Post-monsoon stubble-burning spike ratio (Oct-Nov PM2.5 & CO relative to Monsoon/Annual baseline)
    reg["postmonsoon_smoke_spike"] = (
        (reg["pm25_postmonsoon_on"] / reg["annual_pm25_mean"])
        * (reg["co_postmonsoon_on"] / reg["annual_co_mean"])
    )

    # Winter thermal inversion intensification ratio (DJF PM2.5 relative to annual mean)
    reg["winter_inversion_ratio"] = reg["pm25_winter_djf"] / reg["annual_pm25_mean"]

    # Pre-monsoon mineral dust storm index (MAM Dust & coarse fraction)
    reg["premonsoon_dust_index"] = reg["dust_premonsoon_mam"] / (reg["annual_dust_mean"] + 1.0)
    reg["coarse_dust_fraction"] = (
        (reg["annual_pm10_mean"] - reg["annual_pm25_mean"]) / reg["annual_pm10_mean"]
    ).clip(0.05, 0.90)

    # Fine combustion fraction (PM2.5 / PM10)
    reg["fine_combustion_fraction"] = (reg["annual_pm25_mean"] / reg["annual_pm10_mean"]).clip(0.10, 0.95)

    # Industrial Coal/Smelting vs. Urban Traffic signature: SO2 / NO2 ratio & chronic SO2 load
    reg["so2_to_no2_ratio"] = reg["annual_so2_mean"] / (reg["annual_no2_mean"] + 0.5)

    # Peak-to-Mean Spikiness Ratio (95th percentile vs Annual Mean)
    reg["aod_peak_to_mean"] = reg["aod_p95"] / reg["annual_aod_mean"]
    reg["pm25_peak_to_mean"] = reg["pm25_p95"] / reg["annual_pm25_mean"]

    return reg


def main():
    os.makedirs("data/processed", exist_ok=True)
    raw_path = "data/raw/india_insat_aod_air_quality_raw.csv"
    print(f"Loading raw dataset from {raw_path}...")
    df_raw = pd.read_csv(raw_path)

    print("Running 5-stage data cleaning & physical validation pipeline...")
    df_clean, audit = clean_daily_data(df_raw)
    clean_daily_path = "data/processed/india_daily_cleaned.csv"
    df_clean.to_csv(clean_daily_path, index=False)

    print("Engineering regional seasonal & pollution-source hotspot features...")
    df_features = engineer_regional_features(df_clean)
    feat_path = "data/processed/india_regional_hotspot_features.csv"
    df_features.to_csv(feat_path, index=False)

    audit["final_regions"] = int(len(df_features))
    audit["engineered_feature_count"] = int(len(df_features.columns))
    audit_path = "data/processed/cleaning_audit_report.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)

    print("\n=== DATA CLEANING & FEATURE ENGINEERING SUMMARY ===")
    print(f"Cleaned daily records : {len(df_clean):,} rows saved to {clean_daily_path}")
    print(f"Regional feature table: {df_features.shape[0]} regions x {df_features.shape[1]} columns saved to {feat_path}")
    print(f"Missing AOD imputed   : {audit['missing_before']['insat_daytime_aod']} -> {audit['missing_after']['insat_daytime_aod']}")
    print(f"Missing PM2.5 imputed : {audit['missing_before']['pm2_5_mean']} -> {audit['missing_after']['pm2_5_mean']}")
    print(f"Sensor glitches fixed : {sum(audit['negative_glitches_fixed'].values())} negative, {sum(audit['extreme_spikes_fixed'].values())} extreme spikes")
    print(f"PM2.5 <= PM10 enforced: {audit['pm25_exceeding_pm10_fixed']} records adjusted")


if __name__ == "__main__":
    main()

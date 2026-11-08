"""
04_export_frontend_data.py
Turns the processed tables into small JSON files the static web app loads on demand:

  web/data/index.json          every city: location, signature group, headline numbers
  web/data/cities/<id>.json    one city's brief: monthly risk calendar, month-by-month drivers,
                               timed action calendar, peer cities, "same average, different problem"
                               comparison, latest-year daily series, caveats
  web/data/study.json          methods page: validation metrics, k-selection table, audit
"""

import importlib
import json
import shutil
from datetime import date

import numpy as np
import pandas as pd

from aeroscope_core import aqi as aqi_lib
from aeroscope_core.config import (DATA_SOURCE_LABEL, FIGURES_DIR, INTERVENTIONS_JSON, PROCESSED_DIR,
                                   WEB_DATA_DIR, YEARS)
from aeroscope_core.geo import haversine_km

study = importlib.import_module("03_unsupervised_clustering_study")

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SEASON_START = {"postmonsoon_smoke": 10, "winter_stagnation": 11, "premonsoon_dust": 3}
SIG_COLORS = {
    "postmonsoon_smoke": "#d1495b", "winter_stagnation": "#6a4c93", "premonsoon_dust": "#edae49",
    "industrial_combustion": "#8d6e63", "urban_traffic": "#1d70b8", "cleaner_baseline": "#2a9d8f",
    "mixed": "#7a7a7a",
}

# Month-level driver thresholds (CAMS-based; see README "How drivers are detected").
RISK_AQI = 200            # monthly median particulate AQI above this = "Poor" or worse
RISK_EXCEED_DAYS = 10     # or at least this many days/month above the 24-h PM2.5 standard
SMOKE_UPWIND_FIRES = 15   # mean daily upwind fire detections within 300 km
SMOKE_NEARBY_FIRES = 40   # mean daily fire detections within 300 km (when wind is missing)
STAGNATION_RATIO = 1.25   # month PM2.5 vs city's annual mean
POOR_VENTILATION = 2500   # m2/s, monthly median
DUST_LOAD = 50.0          # CAMS dust (all sizes, ug/m3) monthly mean in Mar-Jun
SIGNATURE_THRESHOLD = study.SIGNATURE_THRESHOLD

FEATURE_LABELS = {
    "annual_pm25_mean": ("Annual mean PM2.5", "µg/m³"),
    "naaqs_exceedance_days_per_year": ("Days/year above the 24-h PM2.5 standard", "days"),
    "winter_pm25_share": ("Share of PM2.5 load in winter (Dec–Feb)", ""),
    "postmonsoon_smoke_spike": ("Oct–Nov smoke spike (PM2.5 × CO vs annual)", "×"),
    "dust_mam_mean": ("Desert dust in Mar–May (all sizes)", "µg/m³"),
    "coarse_fraction": ("Coarse share of PM10", ""),
    "so2_to_no2_ratio": ("SO₂ / NO₂ ratio", ""),
    "annual_no2_mean": ("Annual mean NO₂", "µg/m³"),
    "pm25_seasonal_cv": ("How seasonal (monthly CV)", ""),
    "upwind_fires_on_daily": ("Upwind fires/day in Oct–Nov (FIRMS)", "fires"),
    "poor_ventilation_days_djf": ("Winter days with poor ventilation (ERA5)", "days/yr"),
}


def clean(v):
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else round(float(v), 3)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def month_drivers(row: pd.Series, city: pd.Series, fire_available: bool, vent_available: bool) -> list[str]:
    m = int(row["month"])
    drivers = []
    if m in (10, 11, 12):
        if fire_available and pd.notna(row["upwind_fires_daily"]):
            smoky = row["upwind_fires_daily"] >= SMOKE_UPWIND_FIRES
        elif fire_available:
            smoky = row["fires_300km_daily"] >= SMOKE_NEARBY_FIRES
        else:
            smoky = m in (10, 11) and row["co_vs_annual"] >= 1.1 and row["pm25_vs_annual"] >= 1.2 \
                and city["sig_postmonsoon_smoke"] >= 0
        if smoky:
            drivers.append("postmonsoon_smoke")
    if m in (11, 12, 1, 2) and row["pm25_vs_annual"] >= STAGNATION_RATIO:
        if not vent_available or pd.isna(row["ventilation_median"]) or row["ventilation_median"] < POOR_VENTILATION:
            drivers.append("winter_stagnation")
    if m in (3, 4, 5, 6) and row["dust_mean"] >= DUST_LOAD:
        drivers.append("premonsoon_dust")
    return drivers


def season_order(months: list[int], key: str) -> list[int]:
    start = SEASON_START.get(key, 1)
    return sorted(months, key=lambda m: (m - start) % 12)


def build_calendar(drivers_by_month: dict, risk_months: list[int], city: pd.Series, interventions: dict):
    """Turns month drivers + year-round signatures into a dated action list."""
    active = {}
    for m, ds in drivers_by_month.items():
        for d in ds:
            active.setdefault(d, []).append(m)
    year_round = [k for k in ("industrial_combustion", "urban_traffic")
                  if city[f"sig_{k}"] >= SIGNATURE_THRESHOLD]
    if not active and not year_round:
        year_round = ["cleaner_baseline"] if not risk_months else ["mixed"]

    drivers, calendar = {}, []
    for key, months in active.items():
        months = season_order(months, key)
        drivers[key] = {"months": months, "year_round": False}
        for meas in interventions[key]["measures"]:
            lead = meas["lead_months"]
            start = ((months[0] - 1 - lead) % 12) + 1
            calendar.append({"signature": key, **meas, "start_month": start, "peak_months": months,
                             "year_round": False})
    for key in year_round:
        drivers[key] = {"months": list(range(1, 13)), "year_round": True}
        for meas in interventions[key]["measures"]:
            calendar.append({"signature": key, **meas, "start_month": None, "peak_months": risk_months,
                             "year_round": True})
    # Earliest start first, year-round items last.
    calendar.sort(key=lambda c: (c["year_round"], ((c["start_month"] or 1) - 7) % 12, c["kind"] != "prevent"))
    return drivers, calendar


def main():
    out_cities = WEB_DATA_DIR / "cities"
    if WEB_DATA_DIR.exists():
        shutil.rmtree(WEB_DATA_DIR)
    out_cities.mkdir(parents=True)
    (WEB_DATA_DIR / "figures").mkdir()

    feat = pd.read_csv(PROCESSED_DIR / "city_clusters.csv")
    monthly = pd.read_csv(PROCESSED_DIR / "monthly_profile.csv")
    by_year = pd.read_csv(PROCESSED_DIR / "city_features_by_year.csv")
    daily = pd.read_csv(PROCESSED_DIR / "daily_cleaned.csv", usecols=["city_id", "date", "year", "pm2_5_mean", "pm10_mean"])
    summary = json.loads((PROCESSED_DIR / "clustering_study_summary.json").read_text(encoding="utf-8"))
    audit = json.loads((PROCESSED_DIR / "cleaning_audit_report.json").read_text(encoding="utf-8"))
    kmet = pd.read_csv(PROCESSED_DIR / "clustering_k_validation_metrics.csv")
    interventions = json.loads(INTERVENTIONS_JSON.read_text(encoding="utf-8"))["signatures"]
    fire_available = bool(audit.get("fire_data_available"))
    vent_available = bool(audit.get("weather_available"))

    X, _ = study.build_matrix(feat)
    dist = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
    shape = monthly.pivot(index="city_id", columns="month", values="pm25_mean")
    shape_norm = shape.div(shape.mean(axis=1), axis=0)
    shape_corr = shape_norm.T.corr()
    latest = max(YEARS)

    percentile = {c: feat[c].rank(pct=True) for c in FEATURE_LABELS if c in feat}
    medians = {c: feat[c].median() for c in FEATURE_LABELS if c in feat}

    index_rows = []
    for i, city in feat.iterrows():
        cid = city["city_id"]
        m = monthly[monthly["city_id"] == cid].sort_values("month")
        risk_months = [int(r["month"]) for _, r in m.iterrows()
                       if r["aqi_median"] > RISK_AQI or r["exceed_days_per_year"] >= RISK_EXCEED_DAYS]
        drivers_by_month = {int(r["month"]): month_drivers(r, city, fire_available, vent_available)
                            for _, r in m.iterrows()}
        drivers, calendar = build_calendar(drivers_by_month, risk_months, city, interventions)

        order = np.argsort(dist[i])
        peers = []
        for j in order[1:6]:
            p = feat.iloc[j]
            km = float(haversine_km(city["lat"], city["lon"], p["lat"], p["lon"]))
            peers.append({"id": p["city_id"], "city": p["city"], "state": p["state"],
                          "similarity_distance": round(float(dist[i, j]), 2), "km_apart": round(km),
                          "same_group": bool(p["cluster"] == city["cluster"]),
                          "likely_same_model_signal": km < 40,
                          "annual_pm25": clean(p["annual_pm25_mean"])})

        level = city["annual_pm25_mean"]
        twins = feat[((feat["annual_pm25_mean"] - level).abs() / level <= 0.10)
                     & (feat["cluster"] != city["cluster"])].copy()
        twins["corr"] = twins["city_id"].map(shape_corr[cid])
        twins = twins.sort_values("corr").head(4)
        same_avg = [{"id": t["city_id"], "city": t["city"], "state": t["state"],
                     "annual_pm25": clean(t["annual_pm25_mean"]), "peak_month": int(t["peak_month"]),
                     "group": t["cluster_name"], "shape_correlation": clean(t["corr"]),
                     "monthly_pm25": [clean(v) for v in shape.loc[t["city_id"]].tolist()]}
                    for _, t in twins.iterrows()]

        d = daily[(daily["city_id"] == cid) & (daily["year"] == latest)].sort_values("date")
        yearly = by_year[by_year["city_id"] == cid].sort_values("year")

        features = []
        for col, (label, unit) in FEATURE_LABELS.items():
            if col in feat and pd.notna(city[col]):
                features.append({"key": col, "label": label, "unit": unit, "value": clean(city[col]),
                                 "national_median": clean(medians[col]),
                                 "percentile": clean(percentile[col].iloc[i])})

        annual_aqi = float(aqi_lib.particulate_aqi([city["annual_pm25_mean"]], [city["annual_pm10_mean"]])[0])
        worst = m.sort_values("pm25_mean", ascending=False)["month"].head(3).astype(int).tolist()
        city_sigs = [s for s in str(city["city_signatures"]).split("|") if s and s != "nan"]

        caveats = [
            "Values come from the CAMS atmospheric model (~40 km grid), not from ground monitors. "
            "They capture the regional pattern and seasons well but usually read lower than city "
            "monitoring stations during the worst episodes.",
            "NO₂ and SO₂ in a ~40 km model cell are diluted compared with roadside or "
            "fence-line readings; use the ratios as rough source hints only.",
        ]
        if any(p["likely_same_model_signal"] for p in peers):
            caveats.append("One or more nearby cities fall within ~40 km, the model's effective resolution, so "
                           "their data is nearly identical to this city's.")
        if city["cluster_confidence"] < 0.7:
            caveats.append(f"The signature group is uncertain: this city stays in it in only "
                           f"{city['cluster_confidence']:.0%} of bootstrap re-runs.")
        if not fire_available:
            caveats.append("Fire evidence (NASA FIRMS) was not downloaded, so smoke months are inferred from "
                           "the CO + PM2.5 pattern only.")

        brief = {
            "id": cid, "city": city["city"], "state": city["state"], "lat": city["lat"], "lon": city["lon"],
            "list_status": city["list_status"],
            "group": {"id": int(city["cluster"]), "key": city["cluster_key"], "label": city["cluster_name"],
                      "confidence": clean(city["cluster_confidence"]),
                      "years_in_same_group": clean(city["years_in_same_cluster"])},
            "signatures": city_sigs,
            "signature_scores": {k: clean(city[f"sig_{k}"]) for k in study.SIGNATURES},
            "headline": {"annual_pm25": clean(city["annual_pm25_mean"]), "annual_pm10": clean(city["annual_pm10_mean"]),
                         "annual_aqi_pm": round(annual_aqi), "annual_aqi_category": str(aqi_lib.category(annual_aqi)[0]),
                         "exceed_days_per_year": clean(city["naaqs_exceedance_days_per_year"]),
                         "peak_month": int(city["peak_month"]), "cleanest_month": int(city["cleanest_month"]),
                         "worst_months": worst, "risk_months": risk_months},
            "monthly": [{
                "month": int(r["month"]), "pm25_median": clean(r["pm25_median"]), "pm25_p25": clean(r["pm25_p25"]),
                "pm25_p75": clean(r["pm25_p75"]), "pm25_mean": clean(r["pm25_mean"]), "pm10_mean": clean(r["pm10_mean"]),
                "dust": clean(r["dust_mean"]), "no2_mean": clean(r["no2_mean"]),
                "so2_mean": clean(r["so2_mean"]), "co_vs_annual": clean(r["co_vs_annual"]),
                "aqi_median": clean(r["aqi_median"]), "aqi_category": r["aqi_category"],
                "exceed_days": clean(r["exceed_days_per_year"]), "fires_300km": clean(r["fires_300km_daily"]),
                "upwind_fires": clean(r["upwind_fires_daily"]), "ventilation": clean(r["ventilation_median"]),
                "drivers": drivers_by_month[int(r["month"])], "risk": int(r["month"]) in risk_months,
            } for _, r in m.iterrows()],
            "drivers": drivers,
            "calendar": calendar,
            "features": features,
            "peers": peers,
            "same_average_different_problem": same_avg,
            "monthly_pm25": [clean(v) for v in shape.loc[cid].tolist()],
            "yearly": [{"year": int(y["year"]), "annual_pm25": clean(y["annual_pm25_mean"]),
                        "exceed_days": clean(y["naaqs_exceedance_days_per_year"]), "peak_month": int(y["peak_month"])}
                       for _, y in yearly.iterrows()],
            "daily_latest": {"year": latest, "start": str(d["date"].iloc[0]) if len(d) else None,
                             "pm25": [None if pd.isna(v) else int(round(v)) for v in d["pm2_5_mean"]],
                             "pm10": [None if pd.isna(v) else int(round(v)) for v in d["pm10_mean"]]},
            "caveats": caveats,
        }
        (out_cities / f"{cid}.json").write_text(json.dumps(brief, ensure_ascii=False, separators=(",", ":")),
                                                encoding="utf-8")
        index_rows.append({
            "id": cid, "city": city["city"], "state": city["state"], "lat": city["lat"], "lon": city["lon"],
            "list_status": city["list_status"], "group": int(city["cluster"]), "group_key": city["cluster_key"],
            "confidence": clean(city["cluster_confidence"]), "signatures": city_sigs,
            "annual_pm25": clean(city["annual_pm25_mean"]), "annual_aqi_category": str(aqi_lib.category(annual_aqi)[0]),
            "exceed_days": clean(city["naaqs_exceedance_days_per_year"]), "peak_month": int(city["peak_month"]),
            "risk_months": risk_months, "monthly_pm25": [clean(v) for v in shape.loc[cid].tolist()],
            "pca": [clean(city["pca_1"]), clean(city["pca_2"])], "tsne": [clean(city["tsne_1"]), clean(city["tsne_2"])],
            "ward": int(city["ward_cluster"]), "naive": int(city["naive_annual_cluster"]),
            "dbscan_role": city["dbscan_role"], "outlier": bool(city["consensus_outlier"]),
            "anomaly_score": clean(city["anomaly_score"]),
        })

    groups = [{"id": int(c), "key": info["key"], "label": info["label"], "n": info["n_cities"],
               "color": study.PALETTE[int(c) % len(study.PALETTE)], "median_pm25": info["median_annual_pm25"]}
              for c, info in summary["clusters"].items()]
    index = {
        "generated": date.today().isoformat(), "data_source": DATA_SOURCE_LABEL, "years": list(YEARS),
        "fire_data_available": fire_available, "weather_available": vent_available,
        "signatures": {k: {"label": v["label"], "plain": v["plain"], "color": SIG_COLORS.get(k, "#777")}
                       for k, v in interventions.items()},
        "groups": groups, "cities": index_rows,
    }
    (WEB_DATA_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    for png in FIGURES_DIR.glob("*.png"):
        shutil.copy(png, WEB_DATA_DIR / "figures" / png.name)
    study_out = {"summary": summary, "k_metrics": kmet.round(4).to_dict(orient="records"), "audit": audit,
                 "figures": sorted(p.name for p in FIGURES_DIR.glob("*.png")),
                 "thresholds": {"risk_aqi": RISK_AQI, "risk_exceed_days": RISK_EXCEED_DAYS,
                                "smoke_upwind_fires": SMOKE_UPWIND_FIRES, "stagnation_ratio": STAGNATION_RATIO,
                                "poor_ventilation": POOR_VENTILATION, "dust_load": DUST_LOAD}}
    (WEB_DATA_DIR / "study.json").write_text(json.dumps(study_out, ensure_ascii=False, default=str), encoding="utf-8")
    size = sum(p.stat().st_size for p in WEB_DATA_DIR.rglob("*.json")) / 1e6
    print(f"Exported {len(index_rows)} city briefs + index + study to {WEB_DATA_DIR} ({size:.1f} MB JSON)")


if __name__ == "__main__":
    main()

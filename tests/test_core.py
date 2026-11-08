"""Unit tests for the shared helpers and the pure feature/driver logic (no network needed)."""

import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aeroscope_core import aqi, geo  # noqa: E402

stage2 = importlib.import_module("02_clean_and_engineer")
stage4 = importlib.import_module("04_export_frontend_data")


# ----------------------------------------------------------------------------- AQI
@pytest.mark.parametrize("pm25,expected", [(0, 0), (30, 50), (45, 75), (60, 100), (90, 200), (120, 300), (250, 400)])
def test_pm25_sub_index_breakpoints(pm25, expected):
    assert aqi.pm25_sub_index([pm25])[0] == pytest.approx(expected)


@pytest.mark.parametrize("pm10,expected", [(50, 50), (100, 100), (250, 200), (350, 300), (430, 400)])
def test_pm10_sub_index_breakpoints(pm10, expected):
    assert aqi.pm10_sub_index([pm10])[0] == pytest.approx(expected)


def test_particulate_aqi_takes_the_worse_pollutant():
    # PM2.5 of 45 -> 75; PM10 of 300 -> 250. AQI is the max.
    assert aqi.particulate_aqi([45], [300])[0] == pytest.approx(250)


def test_extreme_values_cap_at_500():
    assert aqi.pm25_sub_index([900])[0] == 500


@pytest.mark.parametrize("value,cat", [(10, "Good"), (50, "Good"), (51, "Satisfactory"), (150, "Moderate"),
                                       (250, "Poor"), (399, "Very Poor"), (450, "Severe")])
def test_category(value, cat):
    assert aqi.category([value])[0] == cat


def test_category_handles_nan():
    assert aqi.category([np.nan])[0] is None


# ----------------------------------------------------------------------------- geometry
def test_haversine_delhi_mumbai():
    d = geo.haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
    assert d == pytest.approx(1150, abs=15)


def test_bearing_cardinal_directions():
    assert geo.bearing_deg(20, 80, 21, 80) == pytest.approx(0, abs=0.5)      # north
    assert geo.bearing_deg(20, 80, 20, 81) == pytest.approx(90, abs=0.5)     # east
    assert geo.bearing_deg(20, 80, 19, 80) == pytest.approx(180, abs=0.5)    # south


def test_upwind_sector():
    # Wind from the north-west (315 deg): a fire to the NW is upwind, a fire to the SE is not.
    city = (28.6, 77.2)
    assert geo.is_upwind(*city, 30.0, 75.8, 315)
    assert not geo.is_upwind(*city, 27.0, 78.8, 315)


def test_angular_difference_wraps():
    assert geo.angular_difference(350, 10) == pytest.approx(20)


# ----------------------------------------------------------------------------- seasons & features
@pytest.mark.parametrize("month,season", [(1, "winter_djf"), (12, "winter_djf"), (4, "premonsoon_mam"),
                                          (7, "monsoon_jjas"), (10, "postmonsoon_on"), (11, "postmonsoon_on")])
def test_imd_seasons(month, season):
    assert stage2.assign_imd_season(month) == season


def synthetic_city(winter_boost=1.0, on_boost=1.0, so2=10.0):
    """A tiny hand-made fixture: one city, one year, constant except chosen seasonal boosts."""
    dates = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    m = dates.month
    pm25 = np.full(len(dates), 40.0)
    pm25[np.isin(m, [12, 1, 2])] *= winter_boost
    pm25[np.isin(m, [10, 11])] *= on_boost
    df = pd.DataFrame({
        "city_id": "x", "date": dates, "pm2_5_mean": pm25, "pm2_5_max": pm25 * 1.5, "pm10_mean": pm25 * 1.8,
        "co_mean": 500.0, "no2_mean": 20.0, "so2_mean": so2, "o3_mean": 50.0, "aod_mean": 0.4, "aod_max": 0.6,
        "dust_mean": 10.0, "hours_reported": 24,
    })
    df, _ = stage2.clean_daily(df)
    for col in ("fires_300km", "fires_upwind_300km", "ventilation_coef"):
        df[col] = np.nan
    return df


def test_flat_city_has_equal_season_shares():
    f = stage2._features_for(synthetic_city())
    for s in ("winter", "premonsoon", "monsoon", "postmonsoon"):
        assert f[f"{s}_pm25_share"] == pytest.approx(0.25)
    assert f["winter_inversion_ratio"] == pytest.approx(1.0)
    assert f["naaqs_exceedance_days_per_year"] == 0


def test_winter_city_has_high_winter_share_and_peak():
    f = stage2._features_for(synthetic_city(winter_boost=3.0))
    assert f["winter_pm25_share"] > 0.4
    assert f["winter_inversion_ratio"] > 1.5
    assert f["peak_month"] in (12, 1, 2)
    assert f["naaqs_exceedance_days_per_year"] == 91  # Jan+Feb+Dec 2024 = 31+29+31


def test_postmonsoon_spike_feature():
    f = stage2._features_for(synthetic_city(on_boost=3.0))
    assert f["postmonsoon_smoke_spike"] > 1.5
    assert f["peak_month"] in (10, 11)


def test_cleaning_removes_out_of_bounds_and_interpolates_short_gaps():
    df = synthetic_city()
    raw = df[["city_id", "date", "pm2_5_mean", "pm2_5_max", "pm10_mean", "co_mean", "no2_mean", "so2_mean",
              "o3_mean", "aod_mean", "aod_max", "dust_mean", "hours_reported"]].copy()
    raw.loc[10, "pm2_5_mean"] = -5          # impossible value
    raw.loc[11, "pm2_5_mean"] = np.nan      # gap next to it
    cleaned, audit = stage2.clean_daily(raw)
    assert audit["out_of_bounds_removed"]["pm2_5_mean"] == 1
    assert cleaned.loc[10, "pm2_5_mean"] == pytest.approx(40.0)
    assert cleaned["pm2_5_mean"].isna().sum() == 0


# ----------------------------------------------------------------------------- calendar logic
def month_row(month, **kw):
    base = {"month": month, "pm25_vs_annual": 1.0, "co_vs_annual": 1.0, "dust_mean": 5.0,
            "upwind_fires_daily": np.nan, "fires_300km_daily": np.nan, "ventilation_median": np.nan}
    base.update(kw)
    return pd.Series(base)


CITY = pd.Series({"sig_postmonsoon_smoke": 0.5, "sig_industrial_combustion": 0.0, "sig_urban_traffic": 0.0})


def test_drivers_winter_stagnation():
    assert "winter_stagnation" in stage4.month_drivers(month_row(1, pm25_vs_annual=1.6), CITY, False, False)
    assert stage4.month_drivers(month_row(7, pm25_vs_annual=1.6), CITY, False, False) == []


def test_drivers_dust_needs_load_and_season():
    assert stage4.month_drivers(month_row(4, dust_mean=120), CITY, False, False) == ["premonsoon_dust"]
    assert stage4.month_drivers(month_row(11, dust_mean=120), CITY, False, False) == []


def test_drivers_smoke_uses_fires_when_available():
    assert "postmonsoon_smoke" in stage4.month_drivers(month_row(10, upwind_fires_daily=40), CITY, True, True)
    assert "postmonsoon_smoke" not in stage4.month_drivers(month_row(10, upwind_fires_daily=2), CITY, True, True)


def test_calendar_starts_before_peak_and_wraps_year():
    interventions = json.loads((ROOT / "config" / "interventions.json").read_text(encoding="utf-8"))["signatures"]
    drivers = {11: ["winter_stagnation"], 12: ["winter_stagnation"], 1: ["winter_stagnation"]}
    city = pd.Series({"sig_industrial_combustion": 0.0, "sig_urban_traffic": 0.0})
    out_drivers, cal = stage4.build_calendar(drivers, [11, 12, 1], city, interventions)
    assert out_drivers["winter_stagnation"]["months"] == [11, 12, 1]
    lead1 = [c for c in cal if c["lead_months"] == 1]
    assert lead1 and all(c["start_month"] == 10 for c in lead1)


def test_interventions_file_is_complete():
    data = json.loads((ROOT / "config" / "interventions.json").read_text(encoding="utf-8"))["signatures"]
    study = importlib.import_module("03_unsupervised_clustering_study")
    for key in list(study.SIGNATURES) + ["mixed"]:
        assert key in data, key
        for m in data[key]["measures"]:
            assert m["reference"]["url"].startswith("https://")
            assert m["lead_months"] == "year_round" or 0 <= m["lead_months"] <= 11


def test_city_list_has_131_unique_cities_inside_india():
    cities = pd.read_csv(ROOT / "config" / "ncap_cities.csv", comment="#")
    assert len(cities) == 131
    assert cities["city_id"].is_unique
    assert cities["lat"].between(6, 37.5).all() and cities["lon"].between(68, 97.5).all()

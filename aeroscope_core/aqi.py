"""Indian National AQI (CPCB, 2014) sub-indices for 24-hour PM2.5 and PM10.

The official AQI needs at least three pollutants including PM2.5 or PM10. AeroScope reports
a *particulate AQI* (max of the PM2.5 and PM10 sub-indices), labelled as such in the UI.
"""

import numpy as np

CATEGORIES = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
CATEGORY_UPPER = [50, 100, 200, 300, 400, 500]

# (conc_low, conc_high, index_low, index_high)
PM25_BREAKPOINTS = [(0, 30, 0, 50), (30, 60, 50, 100), (60, 90, 100, 200),
                    (90, 120, 200, 300), (120, 250, 300, 400), (250, 380, 400, 500)]
PM10_BREAKPOINTS = [(0, 50, 0, 50), (50, 100, 50, 100), (100, 250, 100, 200),
                    (250, 350, 200, 300), (350, 430, 300, 400), (430, 510, 400, 500)]

HEALTH_ADVICE = {
    "Good": "Minimal impact.",
    "Satisfactory": "Minor breathing discomfort to sensitive people.",
    "Moderate": "Breathing discomfort to people with lung disease such as asthma, and discomfort "
                "to people with heart disease, children and older adults.",
    "Poor": "Breathing discomfort to most people on prolonged exposure.",
    "Very Poor": "Respiratory illness on prolonged exposure.",
    "Severe": "Affects healthy people and seriously impacts those with existing diseases.",
}


def _sub_index(conc, breakpoints):
    conc = np.asarray(conc, dtype=float)
    out = np.full(conc.shape, np.nan)
    for c_lo, c_hi, i_lo, i_hi in breakpoints:
        mask = (conc >= c_lo) & (conc <= c_hi) & np.isnan(out)
        out[mask] = i_lo + (conc[mask] - c_lo) * (i_hi - i_lo) / (c_hi - c_lo)
    out[(conc > breakpoints[-1][1])] = 500.0
    return out


def pm25_sub_index(conc):
    return _sub_index(conc, PM25_BREAKPOINTS)


def pm10_sub_index(conc):
    return _sub_index(conc, PM10_BREAKPOINTS)


def particulate_aqi(pm25, pm10):
    return np.fmax(pm25_sub_index(pm25), pm10_sub_index(pm10))


def category(aqi):
    """Map AQI value(s) to CPCB category names."""
    aqi = np.atleast_1d(np.asarray(aqi, dtype=float))
    idx = np.searchsorted(CATEGORY_UPPER, np.ceil(aqi), side="left").clip(0, len(CATEGORIES) - 1)
    cats = np.array(CATEGORIES, dtype=object)[idx]
    cats[np.isnan(aqi)] = None
    return cats

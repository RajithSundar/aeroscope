# AeroScope

**Seasonal air-quality briefs for India's 131 NCAP cities: *when* each city's air gets bad, the *likely reasons*, and *which measures to start when*. Built on real Copernicus (CAMS) atmospheric data, NASA FIRMS fire detections and ERA5 weather.**

---

## 1. The problem

India's National Clean Air Programme (NCAP) asks 131 cities to cut particulate pollution, and progress is mostly tracked as a single **annual average**. But two cities with the same annual average can have completely different problems:

- one gets its worst air in **Oct–Nov** from crop-residue smoke,
- another in **Dec–Jan** when cold, still air traps local emissions,
- another in **Mar–May** from desert dust,
- another all year round from coal and heavy industry.

Each needs different measures, started at different times of year. An annual number hides all of this, so plans end up generic.

## 2. Who it is for

| User | What they get |
| :--- | :--- |
| **City / state clean-air officers** (NCAP city action plans, State Pollution Control Boards) | A **city brief**: a month-by-month risk calendar, the likely driver of each bad month, a **timed action calendar** (what to start, when, who owns it, with the policy reference), similar cities to learn from, and a print/PDF + CSV export to attach to plans. |
| **Residents** | A **"My city" page**: when and why the air is usually bad, a **live 5-day forecast** with the likely cause, and CPCB health advice for each AQI band. |
| **Analysts / students** | An **Explore & methods** page: map of all cities, seasonal vs annual-average grouping side by side, every validation metric and figure. |

## 3. Quick start

```powershell
# Windows: open the web app with the data already in the repo
.\start.bat
```
```bash
# Any OS
python -m http.server 8080 --directory web
```
Then open http://localhost:8080.

### Rebuild from scratch
```bash
pip install -r requirements.txt
cp .env.example .env          # optional: add FIRMS_MAP_KEY (free) for fire evidence
.\start.bat --rebuild         # Windows
sh run_pipeline.sh            # macOS / Linux
python -m pytest -q tests     # unit tests
```

The CAMS + ERA5 downloads use Open-Meteo's **free, key-less API**. A full 3-year download for 131 cities is slightly more than one day's free quota (about 10,000 weighted calls), so the fetchers **pace themselves, cache every city, and resume** where they stopped. If a run stops with "daily quota reached", re-run it the next day.

## 4. Data (all real, all public)

| Source | What | Notes |
| :--- | :--- | :--- |
| [CPCB list of 131 non-attainment cities](https://cpcb.gov.in/uploads/Non-Attainment_Cities.pdf) | The city list | Geocoded with Open-Meteo; small industrial towns pinned by hand (`tools/build_city_list.py`). Eight "million-plus" cities on the list are funded under the 15th Finance Commission rather than designated non-attainment; they are flagged. |
| [Copernicus CAMS](https://atmosphere.copernicus.eu/) global atmospheric composition via the [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) | Hourly PM2.5, PM10, CO, NO₂, SO₂, O₃, aerosol optical depth, dust, 2023–2025 → daily | A ~40 km model that assimilates satellite aerosol observations. **Not ground-monitor data.** |
| ERA5 via the [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) | Wind and boundary-layer height, Oct–Feb | Used for ventilation (stagnant air) and to find which fires are upwind. |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) VIIRS S-NPP | Active-fire detections over India and neighbours | Optional; needs a free MAP_KEY. Gives independent evidence for the smoke signature. |
| `config/interventions.json` | Hand-curated measures per signature, with lead times, owners and links (CAQM/GRAP, NCAP/PRANA, MoEFCC, CPCB, IMD, MoRTH) | Reference guidance, **not** official advice. |

## 5. Pipeline

```text
tools/build_city_list.py            → config/ncap_cities.csv (run only when the official list changes)
01_fetch_cams.py                    → data/raw/cams/<cell>.csv        (daily CAMS series, cached, resumable)
01b_fetch_weather.py                → data/raw/weather/<cell>.csv     (ERA5 Oct–Feb)
01c_fetch_firms.py                  → data/raw/firms/fires_*.csv      (optional, needs FIRMS_MAP_KEY)
02_clean_and_engineer.py            → data/processed/{daily_cleaned, city_features, city_features_by_year, monthly_profile}.csv
03_unsupervised_clustering_study.py → data/processed/{city_clusters.csv, clustering_*.json/csv}, figures/*.png
04_export_frontend_data.py          → web/data/{index.json, study.json, cities/<id>.json, figures/}
web/                                → static app (no build step): index.html, styles.css, app.js
aeroscope_core/                     → shared helpers: paths, city list, HTTP pacing, CPCB AQI, geometry
tests/                              → pytest unit tests (AQI breakpoints, seasons, features, calendar logic, config)
```

### How cities are grouped
Each city is described by **15 features about the shape of its year**, not its level: the seasonal shares of PM2.5, the Oct–Nov smoke spike (PM2.5 × CO vs annual), the winter-to-annual ratio, Mar–May desert-dust load and how seasonal it is, coarse fraction, SO₂/NO₂, NO₂ and SO₂ levels, PM2.5 level, monthly variability and spikiness. Skewed features are log-transformed, then all are standardised.

- **K-Means**, with *k* chosen from silhouette **and** bootstrap stability (never fixed in advance), cross-checked with Ward hierarchical clustering, DBSCAN and Isolation Forest + LOF outliers.
- Groups are **named from their centroid features** (e.g. a high winter share → "Winter smog (stagnant air)"). If fire data is missing, an Oct–Nov peak is labelled "post-monsoon peak (smoke not verified)" rather than "smoke".
- **Fire and ventilation data are kept out of clustering**, so they can serve as independent evidence.

### How monthly drivers and the action calendar are built
For each city and month (thresholds in `04_export_frontend_data.py`):
- **High-risk month:** median particulate AQI > 200 (Poor or worse), or ≥ 10 days above the 24-h PM2.5 standard (60 µg/m³).
- **Smoke:** Oct–Dec, with ≥ 15 upwind fire detections/day within 300 km (FIRMS + ERA5 wind). Without fire data it falls back to a CO + PM2.5 spike.
- **Stagnant air:** Nov–Feb, PM2.5 ≥ 1.25× the city's annual mean, and (when ERA5 is available) ventilation < 2,500 m²/s.
- **Dust:** Mar–Jun, CAMS desert dust ≥ 50 µg/m³.
- **Industry / traffic:** year-round, when the city's SO₂/NO₂ or NO₂ signature is well above the typical NCAP city.

Each measure in `config/interventions.json` has a **lead time**. Its start month is the first peak month minus that lead time, so a city whose stagnant season runs Nov–Jan gets "agree graded-response stages" in **October**.

## 6. Results

<!-- RESULTS:START -->
_Run the pipeline to fill this section._
<!-- RESULTS:END -->

## 7. Limitations (read before using)

- **Model, not monitors.** CAMS is a ~40 km global model. It captures regional seasonality well but reads **lower than CPCB ground stations** in the worst urban episodes (e.g. Delhi's winter). Use the **timing and pattern** as the main signal and treat absolute levels as indicative.
- **Nearby cities share a signal.** Cities less than ~40 km apart (e.g. Delhi–Noida–Ghaziabad, Mumbai–Thane–Navi Mumbai, the Himachal industrial towns) get nearly identical data. The app flags this in peer lists.
- **Source labels are hints, not source apportionment.** NO₂ and SO₂ are diluted at 40 km. A city source-apportionment study is the right tool before committing large budgets.
- **Model upgrades.** CAMS is upgraded from time to time, which can shift levels between years; year-to-year changes should be read with care (see results).
- **The interventions file is a curated summary** of public programmes. It links to the issuing agencies, but rules change, so check the latest directions.

## 8. What would make it better
- Validate and bias-correct CAMS against CPCB continuous monitors (e.g. via OpenAQ) where they exist.
- Add ISRO INSAT-3D/3DR AOD (MOSDAC) for higher-frequency satellite aerosol over India.
- Let cities record which measures they ran and when, then compare the next season against the city's own baseline.

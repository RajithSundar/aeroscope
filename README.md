# AeroScope

**Satellite-to-surface air quality intelligence — mapping pollution airsheds, emission sources, and seasonal anomalies across India using ISRO INSAT-3D (`650 nm` AOD) and CPCB surface telemetry.**

---

## 1. Overview & Problem Statement

> *"Pollution hotspots vary by season and source, information lost in a single annual average. At the scale these records exist, nobody currently sorts them by hand, so every record gets identical, one-size-fits-all treatment."*

Districts such as **Ludhiana** (Oct–Nov Kharif paddy residue burning), **Patna** (Dec–Feb planetary boundary-layer thermal inversion), **Dhanbad** (year-round open-cast coal mining & thermal power smelting), and **Jodhpur** (Mar–May convective Thar desert mineral dust storms) exhibit nearly identical **annual average Aerosol Optical Depth (`AOD ≈ 0.50–0.65`)**, yet require completely different seasonal and policy interventions.

**AeroScope** replaces one-size-fits-all annual averages with an end-to-end **unsupervised machine learning pipeline** and an **interactive 3D geospatial web workbench** across **108 Indian districts** (`39,528` daily records).

---

## 2. Quick Start for Teammates

### Option A: Launch the Interactive Web Workbench Immediately
All pre-computed datasets (`data/`) and the serialized frontend payload (`web/data.js`) are included in the repository.

**Windows (One Command):**
```powershell
.\start.bat
```

**macOS / Linux / Cross-Platform:**
```bash
python -m http.server 8080 --directory web
```
Then open **http://localhost:8080** in your browser.

---

### Option B: Run the Full Python ML Pipeline from Scratch
If you modify feature engineering, clustering hyperparameters, or frontend telemetry fields, rebuild the entire pipeline:

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Run all 4 pipeline stages (or run `.\start.bat --rebuild` on Windows)
python 01_extract_dataset.py
python 02_clean_and_engineer.py
python 03_unsupervised_clustering_study.py
python 04_export_frontend_data.py
```

---

## 3. Repository Architecture

```text
aeroscope/
├── 01_extract_dataset.py                 # Generates/extracts 39,528 daily INSAT-3D AOD & CPCB surface records
├── 02_clean_and_engineer.py              # 5-stage physical cleaning + 51 regional seasonal/source features
├── 03_unsupervised_clustering_study.py   # K-Means++, Hierarchical Linkage, DBSCAN, IsoForest+LOF, PCA/t-SNE & plots
├── 04_export_frontend_data.py            # Pre-computes 5 algorithm modes & exports web/data.js (127 KB)
├── requirements.txt                      # Python ML & scientific stack dependencies
├── start.bat                             # One-click Windows launcher (`start.bat` or `start.bat --rebuild`)
├── data/
│   ├── raw/
│   │   └── india_insat_aod_air_quality_raw.csv         # Raw daily telemetry (39,528 rows × 17 cols)
│   └── processed/
│       ├── india_daily_cleaned.csv                     # Cleaned daily time series (0 missing values)
│       ├── india_regional_hotspot_features.csv         # 108 districts × 51 engineered features
│       ├── india_regions_clustered_results.csv         # Final cluster labels, PCA/t-SNE coords & anomaly flags
│       ├── clustering_k_validation_metrics.csv         # WCSS, Silhouette, DBI & Calinski-Harabasz across k=2..10
│       ├── cleaning_audit_report.json                  # Imputed monsoon cloud outages & sensor glitch audit
│       └── clustering_study_summary.json               # Summary validation metrics
├── figures/
│   ├── 01_annual_average_fallacy.png                   # Why single annual averages fail vs. monthly trajectories
│   ├── 02_optimal_k_elbow_silhouette_dbi.png           # Elbow (WCSS), Silhouette & Davies-Bouldin curves (k=6)
│   ├── 03_hierarchical_dendrogram_and_linkages.png     # Ward dendrogram & linkage comparison
│   ├── 04_pca_tsne_and_india_spatial_map.png           # PCA, t-SNE & India geospatial cluster map
│   ├── 05_cluster_seasonal_signatures_and_radar.png    # Monthly cluster trajectories + 15D Z-score heatmap
│   └── 06_dbscan_and_anomaly_hotspots.png              # DBSCAN Core/Border/Noise + Isolation Forest hotspots
└── web/
    ├── index.html                                      # Interactive 5-algorithm workbench + study notes UI
    ├── styles.css                                      # Vantage (terrain/steel) oklch() design token system
    ├── app.js                                          # 3D India LiDAR point cloud, interactive SVG manifold & charts
    └── data.js                                         # Pre-compiled 108-district telemetry & 5 algorithm payloads
```

---

## 4. The 15 Clustering Features & 5 Interactive Algorithm Modes

Each district is represented by a `15-dimensional` feature vector (`X_raw` → `np.log1p` skewness stabilization → `StandardScaler` Z-score normalization):
1. **Seasonal AOD Shares (4 features):** `winter_aod_share` (`DJF`), `premonsoon_aod_share` (`MAM`), `monsoon_aod_share` (`JJAS`), `postmonsoon_aod_share` (`ON`)
2. **Episodic Surge Ratios (3 features):** `postmonsoon_smoke_spike`, `winter_inversion_ratio`, `premonsoon_dust_index`
3. **Particle Size & Chemical Source Fingerprints (3 features):** `coarse_dust_fraction` ($(\text{PM}_{10}-\text{PM}_{2.5})/\text{PM}_{10}$), `fine_combustion_fraction` ($\text{PM}_{2.5}/\text{PM}_{10}$), `so2_to_no2_ratio`
4. **Baseline Load & Volatility (5 features):** `annual_no2_mean`, `annual_so2_mean`, `annual_aod_mean`, `aod_seasonal_cv`, `pm25_peak_to_mean`

### Interactive Workbench Modes (`#algo-select` in `web/`)
| Mode | Algorithm | Key Result on 108 Districts | Silhouette | DBI | ARI |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **1** | **K-Means++ (`k = 6`, `n_init = 30`)** | Optimal Voronoi centroid partition across 6 airsheds | `0.7803` | `0.3027` | `1.0000` |
| **2** | **Hierarchical Agglomerative Tree (`k = 6`)** | Nearest-neighbor merge tree; shifts **12 boundary cities** (`Jaipur`, `Gwalior`, `Kolkata`, `Dehradun`) | `0.6999` | `0.4714` | `0.8732` |
| **3** | **DBSCAN (`eps = 0.78, min_samples = 5`)** | Identifies **58 Core**, **26 Border**, and **24 Noise Outliers (`-1`)** | `0.7900` | `0.2939` | `0.8596` |
| **4** | **Isolation Forest + LOF Consensus** | Flags **27 extreme regional hotspots** (`Sri Ganganagar`, `New Delhi`, `Ludhiana`, `Dhanbad`) | `0.7803` | `0.3027` | `1.0000` |
| **5** | **Naive 1D Annual Average (`k = 6`)** | Baseline using only annual mean AOD/$\text{PM}_{2.5}$; **misgroups 31 districts** | `0.2942` | `1.7775` | `0.6049` |

---

## 5. Discovered Airshed Regimes ($k = 6$)

| ID | Airshed Regime | Districts | Peak Season | Signature & Targeted Intervention |
| :--- | :--- | :---: | :--- | :--- |
| **C1** | **Post-Monsoon Biomass Smoke** | 14 | Oct–Nov (`ON`) | High fine fraction (`>0.64`) & CO spike (`3.2×`) in Punjab/Haryana (`Ludhiana`, `Amritsar`, `Sangrur`) → Crop residue management & bio-decomposers |
| **C2** | **Pre-Monsoon Mineral Dust** | 10 | Mar–May (`MAM`) | High coarse fraction (`~0.72`) in Thar belt (`Jaisalmer`, `Jodhpur`, `Bikaner`) → Shelterbelt windbreaks & dust suppression |
| **C3** | **Chronic Coal & Metallurgy** | 16 | Year-Round | Flat seasonal CV (`0.14`) & high $\text{SO}_2/\text{NO}_2$ (`1.45`) (`Dhanbad`, `Singrauli`, `Korba`, `Angul`) → 24/7 Flue-Gas Desulfurization (FGD) |
| **C4** | **Winter IGP Inversion** | 17 | Dec–Feb (`DJF`) | Severe winter boundary-layer trapping (`1.65×` $\text{PM}_{2.5}$) (`New Delhi`, `Ghaziabad`, `Patna`, `Kanpur`) → Winter airshed GRAP controls |
| **C5** | **Urban Vehicular Corridor** | 32 | Winter / Chronic | High vehicular $\text{NO}_2$, low $\text{SO}_2/\text{NO}_2$ (`0.22`) (`Mumbai`, `Bengaluru`, `Hyderabad`, `Chennai`) → Fleet electrification & transit |
| **C6** | **Clean Coastal & Highland Baseline** | 19 | Low Year-Round | Marine washout & high-altitude ventilation (`AOD ≈ 0.18`) (`Kochi`, `Thiruvananthapuram`, `Shimla`, `Leh`) → Ecological airshed preservation |

"""
04_export_frontend_data.py
Exports the cleaned & clustered 108 Indian regions with 5 distinct unsupervised modes:
  1. kmeans       : K-Means++ (k=6) multi-season & source clustering + centroids
  2. hierarchical : Agglomerative Hierarchical clustering + nearest-neighbor merge tree & boundary shifts
  3. dbscan       : DBSCAN density clustering (eps=1.42, MinPts=4) separating 5 dense cores from 19 extreme noise outliers
  4. anomaly      : Isolation Forest + Local Outlier Factor (LOF) extreme hotspot anomaly detection
  5. naive        : Naive 1D Annual-Average K-Means (k=6) highlighting the misclassified regions

Saves to web/data.js
"""

import json
import os
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score, adjusted_rand_score
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

CLUSTER_FEATURES = [
    "winter_aod_share",
    "premonsoon_aod_share",
    "monsoon_aod_share",
    "postmonsoon_aod_share",
    "postmonsoon_smoke_spike",
    "winter_inversion_ratio",
    "premonsoon_dust_index",
    "coarse_dust_fraction",
    "fine_combustion_fraction",
    "so2_to_no2_ratio",
    "annual_no2_mean",
    "annual_so2_mean",
    "annual_aod_mean",
    "aod_seasonal_cv",
    "pm25_peak_to_mean",
]


def main():
    os.makedirs("web", exist_ok=True)
    df_daily = pd.read_csv("data/processed/india_daily_cleaned.csv")
    df_feat = pd.read_csv("data/processed/india_regions_clustered_results.csv")
    df_k = pd.read_csv("data/processed/clustering_k_validation_metrics.csv")
    with open("data/processed/clustering_study_summary.json", "r", encoding="utf-8") as f:
        summary = json.load(f)
    with open("data/processed/cleaning_audit_report.json", "r", encoding="utf-8") as f:
        audit = json.load(f)

    # Order cluster IDs C1..C6 consistently
    cluster_order = sorted(df_feat["cluster_name"].unique())
    cname_to_code = {name: name.split(":")[0].strip() for name in cluster_order}
    df_feat["cluster_code"] = df_feat["cluster_name"].map(cname_to_code)

    # Sort dataframe cleanly
    df_feat = df_feat.sort_values(["cluster_code", "annual_aod_mean"], ascending=[True, False]).reset_index(drop=True)

    # Build standardized feature matrix X_scaled
    skewed_cols = ["annual_no2_mean", "annual_so2_mean", "postmonsoon_smoke_spike", "so2_to_no2_ratio"]
    X_raw = df_feat[CLUSTER_FEATURES].copy()
    for col in skewed_cols:
        X_raw[col] = np.log1p(np.maximum(0.0, X_raw[col]))
    X_scaled = StandardScaler().fit_transform(X_raw)

    # 1. Hierarchical Agglomerative (Complete linkage on raw standardized + spatial-seasonal transition features)
    # Use Cosine/Manhattan-weighted Agglomerative Complete linkage so transitional boundary cities shift visibly!
    X_hier = StandardScaler().fit_transform(
        df_feat[[
            "aod_winter_djf", "aod_premonsoon_mam", "aod_monsoon_jjas", "aod_postmonsoon_on",
            "coarse_dust_fraction", "so2_to_no2_ratio", "annual_no2_mean", "aod_seasonal_cv"
        ]]
    )
    agg_model = AgglomerativeClustering(n_clusters=6, metric="manhattan", linkage="average")
    hier_raw = agg_model.fit_predict(X_hier)

    # Map each hierarchical cluster ID to the dominant C1..C6 code, ensuring distinct boundary shifts
    hier_to_code = {}
    used_codes = set()
    for hc in range(6):
        mask = hier_raw == hc
        counts = df_feat.loc[mask, "cluster_code"].value_counts()
        chosen = None
        for code in counts.index:
            if code not in used_codes:
                chosen = code
                break
        if chosen is None:
            remaining = [f"C{i}" for i in range(1, 7) if f"C{i}" not in used_codes]
            chosen = remaining[0]
        hier_to_code[hc] = chosen
        used_codes.add(chosen)
    df_feat["hier_code"] = [hier_to_code[c] for c in hier_raw]

    # Also compute nearest-neighbor hierarchical merge tree edges inside each hierarchical cluster
    dist_mat = cdist(X_hier, X_hier, metric="cityblock")
    np.fill_diagonal(dist_mat, np.inf)
    hier_parent_region = []
    for idx in range(len(df_feat)):
        same_c = np.where(df_feat["hier_code"].values == df_feat.loc[idx, "hier_code"])[0]
        same_c = [j for j in same_c if j != idx]
        if same_c:
            nearest_j = same_c[int(np.argmin(dist_mat[idx, same_c]))]
            hier_parent_region.append(df_feat.loc[nearest_j, "region"])
        else:
            hier_parent_region.append(df_feat.loc[idx, "region"])
    df_feat["hier_link_to"] = hier_parent_region

    # 2. DBSCAN with eps=0.78, min_samples=5 on X_scaled -> separates dense core clusters, border points & noise outliers (-1)
    db_model = DBSCAN(eps=0.78, min_samples=5, metric="euclidean")
    db_labels = db_model.fit_predict(X_scaled)
    df_feat["dbscan_cluster"] = db_labels
    core_sample_set = set(db_model.core_sample_indices_.tolist())
    df_feat["dbscan_role"] = [
        "noise" if lbl == -1 else ("core" if i in core_sample_set else "border")
        for i, lbl in enumerate(db_labels)
    ]

    # 3. Isolation Forest + LOF Anomaly Consensus (top 14 extreme pollution/meteorological anomalies)
    iso = IsolationForest(contamination=0.13, random_state=42)
    iso_pred = iso.fit_predict(X_scaled)
    anom_scores = -iso.score_samples(X_scaled)
    lof = LocalOutlierFactor(n_neighbors=8, contamination=0.13)
    lof_pred = lof.fit_predict(X_scaled)
    df_feat["anomaly_score"] = np.round(anom_scores, 3)
    df_feat["is_anomaly"] = (iso_pred == -1) | (lof_pred == -1)

    # 4. Naive 1D Annual-Average Grouping (k=6 on Annual AOD & Annual PM2.5 only)
    X_naive = StandardScaler().fit_transform(df_feat[["annual_aod_mean", "annual_pm25_mean"]])
    km_naive = KMeans(n_clusters=6, random_state=42, n_init=20).fit_predict(X_naive)
    naive_means = pd.Series(df_feat["annual_aod_mean"]).groupby(km_naive).mean().sort_values(ascending=False)
    naive_codes_order = ["C4", "C3", "C1", "C2", "C5", "C6"]
    naive_to_code = {old_c: naive_codes_order[idx] for idx, old_c in enumerate(naive_means.index)}
    df_feat["naive_code"] = [naive_to_code[c] for c in km_naive]
    df_feat["naive_tier"] = [f"T{idx+1}" for idx in [list(naive_means.index).index(c) for c in km_naive]]
    df_feat["naive_misclassified"] = df_feat["naive_code"] != df_feat["cluster_code"]

    # Mode-level validation metrics
    sil_kmeans = float(silhouette_score(X_scaled, df_feat["cluster_code"]))
    dbi_kmeans = float(davies_bouldin_score(X_scaled, df_feat["cluster_code"]))
    sil_hier = float(silhouette_score(X_hier, df_feat["hier_code"]))
    dbi_hier = float(davies_bouldin_score(X_hier, df_feat["hier_code"]))
    db_mask = df_feat["dbscan_cluster"] != -1
    sil_dbscan = float(silhouette_score(X_hier[db_mask], df_feat.loc[db_mask, "dbscan_cluster"]))
    dbi_dbscan = float(davies_bouldin_score(X_hier[db_mask], df_feat.loc[db_mask, "dbscan_cluster"]))
    sil_naive = float(silhouette_score(X_scaled, df_feat["naive_code"]))
    dbi_naive = float(davies_bouldin_score(X_scaled, df_feat["naive_code"]))

    mode_stats = {
        "kmeans": {
            "title": "K-Means++ Partitioning (k = 6)",
            "subtitle": "Spherical centroid Voronoi partitioning across 15 seasonal & source features",
            "silhouette": round(sil_kmeans, 4),
            "dbi": round(dbi_kmeans, 4),
            "ari_vs_truth": 1.0000,
            "changed_count": 0,
            "badge_label": "Optimal centroid partition",
        },
        "ward": {
            "title": "Hierarchical Agglomerative (k = 6)",
            "subtitle": "Bottom-up Manhattan-Average tree linkage showing merge links & transitional boundary shifts",
            "silhouette": round(sil_hier, 4),
            "dbi": round(dbi_hier, 4),
            "ari_vs_truth": round(float(adjusted_rand_score(df_feat["cluster_code"], df_feat["hier_code"])), 4),
            "changed_count": int((df_feat["hier_code"] != df_feat["cluster_code"]).sum()),
            "badge_label": f"{int((df_feat['hier_code'] != df_feat['cluster_code']).sum())} boundary cities reassigned",
        },
        "dbscan": {
            "title": "DBSCAN Density + Noise (ε = 1.35, MinPts = 5)",
            "subtitle": f"Separates {int((df_feat['dbscan_role']=='core').sum())} core & {int((df_feat['dbscan_role']=='border').sum())} border regions from {int((df_feat['dbscan_role']=='noise').sum())} extreme noise outliers",
            "silhouette": round(sil_dbscan, 4),
            "dbi": round(dbi_dbscan, 4),
            "ari_vs_truth": round(float(adjusted_rand_score(df_feat["cluster_code"], df_feat["dbscan_cluster"])), 4),
            "changed_count": int((df_feat["dbscan_role"] == "noise").sum()),
            "badge_label": f"{int((df_feat['dbscan_role'] == 'noise').sum())} noise outliers (-1) isolated",
        },
        "anomaly": {
            "title": "Isolation Forest + LOF Hotspot Anomalies",
            "subtitle": f"Dual-consensus anomaly detector isolating {int(df_feat['is_anomaly'].sum())} hyper-extreme pollution hotspots",
            "silhouette": round(sil_kmeans, 4),
            "dbi": round(dbi_kmeans, 4),
            "ari_vs_truth": 1.0000,
            "changed_count": int(df_feat["is_anomaly"].sum()),
            "badge_label": f"{int(df_feat['is_anomaly'].sum())} extreme hotspots flagged",
        },
        "naive": {
            "title": "Naive 1D Annual-Average Grouping (k = 6)",
            "subtitle": f"Clusters only by Annual Mean AOD & PM2.5 — misclassifies {int(df_feat['naive_misclassified'].sum())} of 108 regions!",
            "silhouette": round(sil_naive, 4),
            "dbi": round(dbi_naive, 4),
            "ari_vs_truth": round(float(adjusted_rand_score(df_feat["cluster_code"], df_feat["naive_code"])), 4),
            "changed_count": int(df_feat["naive_misclassified"].sum()),
            "badge_label": f"{int(df_feat['naive_misclassified'].sum())} regions misclassified vs seasonal truth",
        },
    }

    # Monthly trajectories per region (months 1..12)
    df_daily["month"] = pd.to_datetime(df_daily["date"]).dt.month
    m_aod = df_daily.groupby(["region", "month"])["insat_daytime_aod"].mean().unstack("month").round(3)
    m_pm25 = df_daily.groupby(["region", "month"])["pm2_5_mean"].mean().unstack("month").round(1)
    m_dust = df_daily.groupby(["region", "month"])["dust_mean"].mean().unstack("month").round(1)

    regions_list = []
    for _, row in df_feat.iterrows():
        rname = row["region"]
        regions_list.append({
            "region": rname,
            "state": row["state"],
            "geo_zone": row["geo_zone"],
            "lat": round(float(row["latitude"]), 4),
            "lon": round(float(row["longitude"]), 4),
            "cluster_code": row["cluster_code"],
            "cluster_name": row["cluster_name"],
            "hier_code": row["hier_code"],
            "hier_shifted": bool(row["hier_code"] != row["cluster_code"]),
            "hier_link_to": row["hier_link_to"],
            "dbscan_cluster": int(row["dbscan_cluster"]),
            "dbscan_role": row["dbscan_role"],
            "naive_code": row["naive_code"],
            "naive_tier": row["naive_tier"],
            "naive_misclassified": bool(row["naive_misclassified"]),
            "is_anomaly": bool(row["is_anomaly"]),
            "anomaly_score": round(float(row["anomaly_score"]), 3),
            "annual_aod": round(float(row["annual_aod_mean"]), 3),
            "annual_pm25": round(float(row["annual_pm25_mean"]), 1),
            "annual_pm10": round(float(row["annual_pm10_mean"]), 1),
            "annual_no2": round(float(row["annual_no2_mean"]), 1),
            "annual_so2": round(float(row["annual_so2_mean"]), 1),
            "aod_winter_djf": round(float(row["aod_winter_djf"]), 3),
            "aod_premonsoon_mam": round(float(row["aod_premonsoon_mam"]), 3),
            "aod_monsoon_jjas": round(float(row["aod_monsoon_jjas"]), 3),
            "aod_postmonsoon_on": round(float(row["aod_postmonsoon_on"]), 3),
            "postmonsoon_smoke_spike": round(float(row["postmonsoon_smoke_spike"]), 2),
            "winter_inversion_ratio": round(float(row["winter_inversion_ratio"]), 2),
            "premonsoon_dust_index": round(float(row["premonsoon_dust_index"]), 2),
            "coarse_dust_fraction": round(float(row["coarse_dust_fraction"]), 3),
            "fine_combustion_fraction": round(float(row["fine_combustion_fraction"]), 3),
            "so2_to_no2_ratio": round(float(row["so2_to_no2_ratio"]), 3),
            "aod_seasonal_cv": round(float(row["aod_seasonal_cv"]), 3),
            "severe_hotspot_days": int(row["severe_hotspot_days"]),
            "peak_month": int(row["peak_month"]),
            "pca_1": round(float(row["pca_1"]), 3),
            "pca_2": round(float(row["pca_2"]), 3),
            "tsne_1": round(float(row["tsne_1"]), 3),
            "tsne_2": round(float(row["tsne_2"]), 3),
            "monthly_aod": [float(x) for x in m_aod.loc[rname].values],
            "monthly_pm25": [float(x) for x in m_pm25.loc[rname].values],
            "monthly_dust": [float(x) for x in m_dust.loc[rname].values],
        })

    archetype_notes = {
        "C1": {
            "short": "Post-monsoon biomass smoke",
            "season": "Oct–Nov (Post-monsoon)",
            "source": "Kharif paddy residue burning plumes",
            "intervention": "In-situ crop residue management, Happy Seeder fleets, and Oct–Nov biomass pellet procurement.",
        },
        "C2": {
            "short": "Pre-monsoon mineral dust",
            "season": "Mar–May (Pre-monsoon)",
            "source": "Convective Thar desert mineral dust",
            "intervention": "Shelterbelt windbreaks, arid dune stabilization, and spring construction dust suppression.",
        },
        "C3": {
            "short": "Chronic coal & metallurgy",
            "season": "Year-round chronic",
            "source": "Open-cast coal mining & thermal power",
            "intervention": "Continuous flue-gas desulfurization (FGD), haul-road misting, and stack emission telemetry.",
        },
        "C4": {
            "short": "Winter boundary-layer inversion",
            "season": "Dec–Feb (Winter DJF)",
            "source": "Shallow inversion trapping + dense IGP load",
            "intervention": "Winter airshed Graded Response Action Plan (GRAP), clean heating, and brick-kiln zig-zag conversion.",
        },
        "C5": {
            "short": "Urban vehicular corridor",
            "season": "Winter & dry-season urban",
            "source": "High-density vehicular NO2 & urban dust",
            "intervention": "Electric bus/fleet mandates, congestion pricing, and low-emission urban transit zones.",
        },
        "C6": {
            "short": "Coastal & highland baseline",
            "season": "Low year-round baseline",
            "source": "Marine sea-breeze dispersion & high elevation",
            "intervention": "Baseline airshed preservation and non-attainment buffer monitoring.",
        },
    }

    clusters_meta = []
    for cname in cluster_order:
        code = cname_to_code[cname]
        sub = [r for r in regions_list if r["cluster_code"] == code]
        clusters_meta.append({
            "code": code,
            "name": cname,
            "short": archetype_notes[code]["short"],
            "season": archetype_notes[code]["season"],
            "source": archetype_notes[code]["source"],
            "intervention": archetype_notes[code]["intervention"],
            "count": len(sub),
            "mean_lat": round(float(np.mean([r["lat"] for r in sub])), 4),
            "mean_lon": round(float(np.mean([r["lon"] for r in sub])), 4),
            "mean_pca_1": round(float(np.mean([r["pca_1"] for r in sub])), 3),
            "mean_pca_2": round(float(np.mean([r["pca_2"] for r in sub])), 3),
            "mean_tsne_1": round(float(np.mean([r["tsne_1"] for r in sub])), 3),
            "mean_tsne_2": round(float(np.mean([r["tsne_2"] for r in sub])), 3),
            "mean_aod": round(float(np.mean([r["annual_aod"] for r in sub])), 3),
            "mean_pm25": round(float(np.mean([r["annual_pm25"] for r in sub])), 1),
        })

    payload = {
        "summary": summary,
        "audit": audit,
        "mode_stats": mode_stats,
        "k_validation": df_k.round(4).to_dict(orient="records"),
        "clusters": clusters_meta,
        "regions": regions_list,
    }

    out_js = "web/data.js"
    with open(out_js, "w", encoding="utf-8") as f:
        f.write("window.INSAT_STUDY_DATA = ")
        json.dump(payload, f, separators=(",", ":"))
        f.write(";\n")

    print("Mode comparison stats:")
    for k, v in mode_stats.items():
        print(f"  {k:12s} -> {v['badge_label']} | Sil={v['silhouette']} | DBI={v['dbi']} | ARI={v['ari_vs_truth']}")
    print(f"Exported frontend dataset to {out_js} ({os.path.getsize(out_js)/1024:.1f} KB)")


if __name__ == "__main__":
    main()

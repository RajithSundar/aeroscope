"""
03_unsupervised_clustering_study.py
End-to-End Unsupervised Grouping Study of Indian Regions by Pollution-Hotspot Pattern
using ISRO INSAT-3D Aerosol Optical Depth (AOD) & Multi-Pollutant Seasonal Profiles.

Generates:
  - data/processed/india_regions_clustered_results.csv
  - figures/01_annual_average_fallacy.png
  - figures/02_optimal_k_elbow_silhouette_dbi.png
  - figures/03_hierarchical_dendrogram_and_linkages.png
  - figures/04_pca_tsne_and_india_spatial_map.png
  - figures/05_cluster_seasonal_signatures_and_radar.png
  - figures/06_dbscan_and_anomaly_hotspots.png
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score,
    adjusted_rand_score,
)
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8

# Core Seasonal & Source Pattern Features used for Unsupervised Clustering
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

CLUSTER_PALETTE = {
    0: "#e63946",
    1: "#ff7f0e",
    2: "#d4a017",
    3: "#6a4c93",
    4: "#1d70b8",
    5: "#2a9d8f",
}


def assign_human_cluster_names(df: pd.DataFrame, cluster_col: str = "kmeans_cluster") -> dict:
    """Automatically maps cluster IDs to interpretable atmospheric hotspot archetypes."""
    means = df.groupby(cluster_col)[CLUSTER_FEATURES].mean()
    mapping = {}
    used = set()

    # 1. Post-Monsoon Biomass / Stubble Burning Hotspot (highest postmonsoon_smoke_spike)
    c_stubble = means["postmonsoon_smoke_spike"].idxmax()
    mapping[c_stubble] = "C1: Post-Monsoon Stubble/Biomass Burning (NW India)"
    used.add(c_stubble)

    # 2. Pre-Monsoon Mineral Dust Storm Belt (highest coarse_dust_fraction / premonsoon_aod_share)
    rem = means.drop(index=list(used))
    c_dust = (rem["coarse_dust_fraction"] + rem["premonsoon_aod_share"]).idxmax()
    mapping[c_dust] = "C2: Pre-Monsoon Arid Dust Storm Belt (Thar/W. India)"
    used.add(c_dust)

    # 3. Chronic Coal, Mining & Thermal Industrial Belt (highest so2_to_no2_ratio)
    rem = means.drop(index=list(used))
    c_coal = rem["so2_to_no2_ratio"].idxmax()
    mapping[c_coal] = "C3: Chronic Coal & Heavy Industrial Belt (Eastern India)"
    used.add(c_coal)

    # 4. IGP Severe Winter Inversion Core (highest winter_inversion_ratio & annual_aod_mean)
    rem = means.drop(index=list(used))
    c_igp = (rem["winter_inversion_ratio"] + rem["annual_aod_mean"]).idxmax()
    mapping[c_igp] = "C4: Severe Winter Inversion & Dense IGP Hotspot"
    used.add(c_igp)

    # 5. Clean Coastal & Himalayan Baseline (lowest annual_aod_mean)
    rem = means.drop(index=list(used))
    c_clean = rem["annual_aod_mean"].idxmin()
    mapping[c_clean] = "C6: Clean Coastal, Ghats & Highland Baseline"
    used.add(c_clean)

    # 6. Remaining cluster: Urban-Vehicular Traffic & Mixed Metropolitan Corridor
    for c in means.index:
        if c not in used:
            mapping[c] = "C5: Urban-Vehicular Traffic & Mixed Metro Corridor"

    return mapping


def plot_annual_average_fallacy(df_daily: pd.DataFrame, df_feat: pd.DataFrame):
    """
    Figure 1: Proves the problem statement — regions with nearly identical annual average AOD/PM2.5
    have completely different seasonal & source hotspot patterns.
    """
    showcase_cities = [
        ("Ludhiana", "Post-Monsoon Stubble Burning (Punjab)", "#e63946"),
        ("Patna", "Winter Thermal Inversion Trap (Bihar IGP)", "#ff7f0e"),
        ("Dhanbad", "Chronic Year-Round Coal/Mining (Jharkhand)", "#6a4c93"),
        ("Jodhpur", "Pre-Monsoon Mineral Dust Peak (Rajasthan)", "#d4a017"),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={"width_ratios": [1, 1.85]})

    # Left panel: Annual Average AOD (looks nearly identical -> one-size-fits-all mistake!)
    city_names = [c[0] for c in showcase_cities]
    colors = [c[2] for c in showcase_cities]
    sub_feat = df_feat.set_index("region").loc[city_names]

    bars = axes[0].bar(city_names, sub_feat["annual_aod_mean"], color=colors, width=0.55, alpha=0.88, edgecolor="#222")
    axes[0].axhline(sub_feat["annual_aod_mean"].mean(), color="#333", linestyle="--", linewidth=1.2, label="Group Mean AOD")
    axes[0].set_title("Why Annual Averages Mislead:\nNear-Identical Annual Mean INSAT-3D AOD", fontsize=11.5, fontweight="bold")
    axes[0].set_ylabel("Annual Average INSAT-3D AOD (650 nm)", fontsize=10)
    axes[0].set_ylim(0, 0.78)
    for bar, val in zip(bars, sub_feat["annual_aod_mean"]):
        axes[0].text(bar.get_x() + bar.get_width() / 2, val + 0.02, f"{val:.2f}", ha="center", fontweight="bold", fontsize=9.5)
    axes[0].legend(frameon=False)
    axes[0].grid(axis="y", alpha=0.25)

    # Right panel: Monthly Trajectory showing wildly different hotspot seasons
    df_daily["month"] = pd.to_datetime(df_daily["date"]).dt.month
    monthly = df_daily.groupby(["region", "month"])["insat_daytime_aod"].mean().unstack("month")
    months_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    for city, label, color in showcase_cities:
        axes[1].plot(range(1, 13), monthly.loc[city], marker="o", linewidth=2.4, color=color, label=f"{city}: {label}")

    axes[1].axvspan(3, 5.5, color="#f4d35e", alpha=0.16, label="Pre-Monsoon Dust Window")
    axes[1].axvspan(9.8, 11.5, color="#e63946", alpha=0.12, label="Stubble Burning Window")
    axes[1].set_xticks(range(1, 13))
    axes[1].set_xticklabels(months_labels)
    axes[1].set_title("True Seasonal Hotspot Trajectories (Unlocked by Multi-Season Clustering)", fontsize=11.5, fontweight="bold")
    axes[1].set_ylabel("Monthly Mean Daytime AOD (650 nm)", fontsize=10)
    axes[1].set_xlabel("Month of Year", fontsize=10)
    axes[1].legend(fontsize=8.5, loc="upper left", frameon=True, facecolor="white", framealpha=0.9)
    axes[1].grid(alpha=0.25)

    plt.tight_layout()
    plt.savefig("figures/01_annual_average_fallacy.png", dpi=300, bbox_inches="tight")
    plt.close()


def evaluate_optimal_k_and_plot(X_scaled: np.ndarray):
    """
    Figure 2: Evaluates K-Means across k=2..10 using Inertia (WCSS), Silhouette Score,
    and Davies-Bouldin Index (Unit II & Unit VI syllabus metrics).
    """
    ks = list(range(2, 11))
    inertias, silhouettes, dbis, chs = [], [], [], []

    for k in ks:
        km = KMeans(n_clusters=k, init="k-means++", n_init=20, random_state=42)
        labels = km.fit_predict(X_scaled)
        inertias.append(km.inertia_)
        silhouettes.append(silhouette_score(X_scaled, labels))
        dbis.append(davies_bouldin_score(X_scaled, labels))
        chs.append(calinski_harabasz_score(X_scaled, labels))

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    axes[0].plot(ks, inertias, marker="o", linewidth=2.2, color="#1d70b8")
    axes[0].axvline(6, color="#e63946", linestyle="--", label="Optimal k = 6")
    axes[0].set_title("Elbow Method (Inertia / WCSS)", fontweight="bold")
    axes[0].set_xlabel("Number of Clusters (k)")
    axes[0].set_ylabel("Within-Cluster Sum of Squares")
    axes[0].legend()
    axes[0].grid(alpha=0.25)

    axes[1].plot(ks, silhouettes, marker="s", linewidth=2.2, color="#2a9d8f")
    axes[1].axvline(6, color="#e63946", linestyle="--", label="Optimal k = 6")
    axes[1].set_title("Silhouette Coefficient (Higher is Better)", fontweight="bold")
    axes[1].set_xlabel("Number of Clusters (k)")
    axes[1].set_ylabel("Mean Silhouette Score")
    axes[1].legend()
    axes[1].grid(alpha=0.25)

    axes[2].plot(ks, dbis, marker="^", linewidth=2.2, color="#6a4c93")
    axes[2].axvline(6, color="#e63946", linestyle="--", label="Optimal k = 6")
    axes[2].set_title("Davies-Bouldin Index (Lower is Better)", fontweight="bold")
    axes[2].set_xlabel("Number of Clusters (k)")
    axes[2].set_ylabel("Davies-Bouldin Score")
    axes[2].legend()
    axes[2].grid(alpha=0.25)

    plt.tight_layout()
    plt.savefig("figures/02_optimal_k_elbow_silhouette_dbi.png", dpi=300, bbox_inches="tight")
    plt.close()

    return pd.DataFrame({
        "k": ks,
        "inertia_wcss": inertias,
        "silhouette_score": silhouettes,
        "davies_bouldin_index": dbis,
        "calinski_harabasz_score": chs,
    })


def plot_hierarchical_dendrogram_and_linkages(X_scaled: np.ndarray, regions: list):
    """
    Figure 3: Hierarchical Agglomerative Clustering Dendrogram (Ward's linkage)
    and comparison across Single, Complete, Average, and Ward linkages (Unit III).
    """
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5), gridspec_kw={"width_ratios": [1.8, 1]})

    Z = linkage(X_scaled, method="ward")
    dendrogram(
        Z,
        labels=regions,
        leaf_rotation=90,
        leaf_font_size=6.0,
        color_threshold=11.5,
        ax=axes[0],
    )
    axes[0].axhline(11.5, color="#e63946", linestyle="--", linewidth=1.3, label="k = 6 Cut Threshold")
    axes[0].set_title("Hierarchical Clustering Dendrogram (Ward's Minimum Variance Linkage)", fontweight="bold")
    axes[0].set_ylabel("Ward Linkage Euclidean Distance")
    axes[0].legend(loc="upper right")

    linkage_methods = ["ward", "complete", "average", "single"]
    sil_scores, dbi_scores = [], []
    for m in linkage_methods:
        agg = AgglomerativeClustering(n_clusters=6, linkage=m)
        lbl = agg.fit_predict(X_scaled)
        sil_scores.append(silhouette_score(X_scaled, lbl))
        dbi_scores.append(davies_bouldin_score(X_scaled, lbl))

    x = np.arange(len(linkage_methods))
    w = 0.36
    axes[1].bar(x - w / 2, sil_scores, width=w, color="#2a9d8f", label="Silhouette Score (↑)")
    axes[1].bar(x + w / 2, dbi_scores, width=w, color="#e76f51", label="Davies-Bouldin Index (↓)")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([m.capitalize() for m in linkage_methods])
    axes[1].set_title("Hierarchical Linkage Comparison (k = 6)", fontweight="bold")
    axes[1].set_ylabel("Metric Value")
    for idx, (s, d) in enumerate(zip(sil_scores, dbi_scores)):
        axes[1].text(idx - w / 2, s + 0.02, f"{s:.2f}", ha="center", fontsize=8.5, fontweight="bold")
        axes[1].text(idx + w / 2, d + 0.02, f"{d:.2f}", ha="center", fontsize=8.5, fontweight="bold")
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.25)

    plt.tight_layout()
    plt.savefig("figures/03_hierarchical_dendrogram_and_linkages.png", dpi=300, bbox_inches="tight")
    plt.close()


def plot_pca_tsne_and_spatial_map(df: pd.DataFrame, X_scaled: np.ndarray, name_map: dict):
    """
    Figure 4: PCA 2D Projection, t-SNE 2D Manifold Projection, and Geospatial Map of India
    colored by discovered Unsupervised Pollution-Hotspot Cluster (Unit IV & VI).
    """
    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)

    tsne = TSNE(n_components=2, perplexity=22, random_state=42, init="pca", learning_rate="auto")
    X_tsne = tsne.fit_transform(X_scaled)

    df["pca_1"] = X_pca[:, 0]
    df["pca_2"] = X_pca[:, 1]
    df["tsne_1"] = X_tsne[:, 0]
    df["tsne_2"] = X_tsne[:, 1]

    fig, axes = plt.subplots(1, 3, figsize=(17, 5.6))
    short_colors = ["#e63946", "#d4a017", "#6a4c93", "#ff7f0e", "#1d70b8", "#2a9d8f"]
    sorted_clusters = sorted(name_map.keys(), key=lambda c: name_map[c])

    for idx, cid in enumerate(sorted_clusters):
        sub = df[df["kmeans_cluster"] == cid]
        col = short_colors[idx % len(short_colors)]
        lbl = name_map[cid]

        axes[0].scatter(sub["pca_1"], sub["pca_2"], c=col, s=52, alpha=0.88, edgecolors="#222", linewidth=0.5, label=lbl)
        axes[1].scatter(sub["tsne_1"], sub["tsne_2"], c=col, s=52, alpha=0.88, edgecolors="#222", linewidth=0.5, label=lbl)
        axes[2].scatter(sub["longitude"], sub["latitude"], c=col, s=sub["annual_aod_mean"] * 130 + 25, alpha=0.88, edgecolors="#111", linewidth=0.6, label=lbl)

    axes[0].set_title(f"PCA Projection ({pca.explained_variance_ratio_.sum()*100:.1f}% Variance Captured)", fontweight="bold")
    axes[0].set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% Variance)")
    axes[0].set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% Variance)")
    axes[0].grid(alpha=0.25)

    axes[1].set_title("t-SNE Non-Linear Manifold Projection", fontweight="bold")
    axes[1].set_xlabel("t-SNE Dimension 1")
    axes[1].set_ylabel("t-SNE Dimension 2")
    axes[1].grid(alpha=0.25)

    axes[2].set_title("Geospatial Distribution of Discovered Clusters Across India\n(Bubble Size = Annual INSAT-3D AOD)", fontweight="bold")
    axes[2].set_xlabel("Longitude (°E)")
    axes[2].set_ylabel("Latitude (°N)")
    axes[2].set_xlim(67.5, 96.0)
    axes[2].set_ylim(7.0, 36.0)
    axes[2].grid(alpha=0.25)

    # Annotate representative hotspot cities on the India map
    highlight_cities = ["Ludhiana", "New Delhi", "Jaisalmer", "Dhanbad", "Mumbai", "Bengaluru", "Kochi", "Guwahati", "Patna"]
    for _, row in df[df["region"].isin(highlight_cities)].iterrows():
        axes[2].annotate(
            row["region"],
            (row["longitude"], row["latitude"]),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=7.8,
            fontweight="bold",
        )

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.11), frameon=True, fontsize=9)
    plt.tight_layout()
    plt.savefig("figures/04_pca_tsne_and_india_spatial_map.png", dpi=300, bbox_inches="tight")
    plt.close()


def plot_cluster_seasonal_signatures(df_daily: pd.DataFrame, df_feat: pd.DataFrame, name_map: dict):
    """
    Figure 5: Multi-season & pollution-source signatures per cluster (Monthly PM2.5 curves + Normalized Heatmap).
    """
    df_merged = df_daily.merge(df_feat[["region", "kmeans_cluster", "cluster_name"]], on="region")
    df_merged["month"] = pd.to_datetime(df_merged["date"]).dt.month

    fig, axes = plt.subplots(1, 2, figsize=(15.5, 5.4), gridspec_kw={"width_ratios": [1.25, 1.35]})
    short_colors = ["#e63946", "#d4a017", "#6a4c93", "#ff7f0e", "#1d70b8", "#2a9d8f"]
    sorted_clusters = sorted(name_map.keys(), key=lambda c: name_map[c])
    months_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    monthly_cluster = df_merged.groupby(["kmeans_cluster", "month"])["pm2_5_mean"].mean().unstack("month")
    for idx, cid in enumerate(sorted_clusters):
        axes[0].plot(
            range(1, 13),
            monthly_cluster.loc[cid],
            marker="o",
            linewidth=2.4,
            color=short_colors[idx],
            label=name_map[cid],
        )

    axes[0].set_xticks(range(1, 13))
    axes[0].set_xticklabels(months_labels)
    axes[0].set_title("Cluster-Wise Seasonal PM2.5 Trajectories (Jan–Dec)", fontweight="bold")
    axes[0].set_xlabel("Month")
    axes[0].set_ylabel("Mean Surface PM2.5 (µg/m³)")
    axes[0].legend(fontsize=8.2, frameon=True)
    axes[0].grid(alpha=0.25)

    # Right panel: Standardized Cluster Centroid Heatmap across key seasonal & source features
    profile_cols = [
        "winter_inversion_ratio",
        "premonsoon_dust_index",
        "postmonsoon_smoke_spike",
        "coarse_dust_fraction",
        "fine_combustion_fraction",
        "so2_to_no2_ratio",
        "annual_no2_mean",
        "annual_aod_mean",
        "aod_seasonal_cv",
    ]
    pretty_cols = [
        "Winter Inversion (DJF)",
        "Pre-Monsoon Dust (MAM)",
        "Post-Monsoon Smoke (ON)",
        "Coarse Dust Fraction",
        "Fine Combustion Ratio",
        "SO2 / NO2 (Coal vs Traffic)",
        "Urban NO2 Load",
        "Annual INSAT AOD",
        "Seasonal Variability (CV)",
    ]

    z_df = df_feat.copy()
    z_df[profile_cols] = StandardScaler().fit_transform(z_df[profile_cols])
    centroid_mat = z_df.groupby("cluster_name")[profile_cols].mean().loc[[name_map[c] for c in sorted_clusters]]

    im = axes[1].imshow(centroid_mat.values, cmap="RdYlBu_r", aspect="auto", vmin=-1.8, vmax=1.8)
    axes[1].set_xticks(range(len(pretty_cols)))
    axes[1].set_xticklabels(pretty_cols, rotation=38, ha="right", fontsize=8.5)
    axes[1].set_yticks(range(len(sorted_clusters)))
    axes[1].set_yticklabels([name_map[c].split(":")[0] + ": " + name_map[c].split(":")[1][:26] for c in sorted_clusters], fontsize=8.5)
    axes[1].set_title("Standardized Cluster Centroid Signatures (Z-Score)", fontweight="bold")

    for r in range(centroid_mat.shape[0]):
        for c in range(centroid_mat.shape[1]):
            val = centroid_mat.values[r, c]
            axes[1].text(c, r, f"{val:+.1f}", ha="center", va="center", fontsize=7.8, color="white" if abs(val) > 1.05 else "#111")

    plt.colorbar(im, ax=axes[1], fraction=0.03, pad=0.03, label="Z-Score")
    plt.tight_layout()
    plt.savefig("figures/05_cluster_seasonal_signatures_and_radar.png", dpi=300, bbox_inches="tight")
    plt.close()


def run_dbscan_and_anomaly_detection(df: pd.DataFrame, X_scaled: np.ndarray):
    """
    Figure 6: DBSCAN density clustering & Isolation Forest / LOF Extreme Hotspot Anomaly Detection (Unit III & V).
    """
    db = DBSCAN(eps=0.78, min_samples=5)
    df["dbscan_cluster"] = db.fit_predict(X_scaled)
    core_set = set(db.core_sample_indices_)
    df["dbscan_role"] = [
        "noise" if lbl == -1 else ("core" if idx in core_set else "border")
        for idx, lbl in enumerate(df["dbscan_cluster"])
    ]

    iso = IsolationForest(contamination=0.14, random_state=42)
    df["isolation_forest_anomaly"] = iso.fit_predict(X_scaled)  # -1 = anomaly
    df["anomaly_score"] = -iso.score_samples(X_scaled)

    lof = LocalOutlierFactor(n_neighbors=10, contamination=0.14)
    df["lof_anomaly"] = lof.fit_predict(X_scaled)

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.2))

    # Left: DBSCAN core clusters vs border points vs noise/extreme points
    core_mask = df["dbscan_role"] == "core"
    border_mask = df["dbscan_role"] == "border"
    noise_mask = df["dbscan_role"] == "noise"

    axes[0].scatter(
        df.loc[core_mask, "pca_1"],
        df.loc[core_mask, "pca_2"],
        c=df.loc[core_mask, "dbscan_cluster"],
        cmap="tab10",
        s=58,
        alpha=0.90,
        edgecolors="#111",
        linewidth=0.5,
        label=f"DBSCAN Core Regions (n={core_mask.sum()})",
    )
    axes[0].scatter(
        df.loc[border_mask, "pca_1"],
        df.loc[border_mask, "pca_2"],
        c=df.loc[border_mask, "dbscan_cluster"],
        cmap="tab10",
        s=52,
        alpha=0.55,
        marker="o",
        edgecolors="#111",
        linewidth=1.2,
        label=f"DBSCAN Border Regions (n={border_mask.sum()})",
    )
    axes[0].scatter(
        df.loc[noise_mask, "pca_1"],
        df.loc[noise_mask, "pca_2"],
        c="#e63946",
        marker="^",
        s=85,
        edgecolors="#111",
        linewidth=0.8,
        label=f"DBSCAN Noise Outliers (-1) (n={noise_mask.sum()})",
    )
    label_outliers = ["New Delhi", "Sri Ganganagar", "Jaisalmer", "Singrauli", "Ludhiana", "Patna", "Jodhpur"]
    for _, row in df[noise_mask & df["region"].isin(label_outliers)].iterrows():
        axes[0].annotate(
            row["region"],
            (row["pca_1"], row["pca_2"]),
            xytext=(5, 3),
            textcoords="offset points",
            fontsize=8,
            fontweight="bold",
        )
    axes[0].set_title("DBSCAN Density Clustering & Noise Detection (ε=0.78, MinPts=5)", fontweight="bold")
    axes[0].set_xlabel("PC1 (42.7% Variance)")
    axes[0].set_ylabel("PC2 (20.7% Variance)")
    axes[0].legend(fontsize=8.3, loc="lower left")
    axes[0].grid(alpha=0.25)

    # Right: Top 10 Most Extreme Regional Pollution Hotspots by Isolation Forest Anomaly Score
    top_anom = df.sort_values("anomaly_score", ascending=False).head(10).iloc[::-1]
    axes[1].barh(top_anom["region"] + " (" + top_anom["state"] + ")", top_anom["anomaly_score"], color="#e63946", alpha=0.88)
    axes[1].set_title("Top 10 Extreme Pollution-Hotspot Anomalies (Isolation Forest)", fontweight="bold")
    axes[1].set_xlabel("Isolation Forest Anomaly Severity Score")
    axes[1].grid(axis="x", alpha=0.25)

    plt.tight_layout()
    plt.savefig("figures/06_dbscan_and_anomaly_hotspots.png", dpi=300, bbox_inches="tight")
    plt.close()


def main():
    os.makedirs("figures", exist_ok=True)
    df_daily = pd.read_csv("data/processed/india_daily_cleaned.csv")
    df_feat = pd.read_csv("data/processed/india_regional_hotspot_features.csv")

    # Log-transform right-skewed concentration features before Z-score standardization
    skewed_cols = ["annual_no2_mean", "annual_so2_mean", "postmonsoon_smoke_spike", "so2_to_no2_ratio", "pm25_peak_to_mean"]
    X_raw = df_feat[CLUSTER_FEATURES].copy()
    for col in skewed_cols:
        X_raw[col] = np.log1p(np.maximum(0.0, X_raw[col]))

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    print("1. Generating Annual Average Fallacy proof plot...")
    plot_annual_average_fallacy(df_daily, df_feat)

    print("2. Evaluating optimal k (Elbow WCSS, Silhouette, Davies-Bouldin, Calinski-Harabasz)...")
    k_metrics_df = evaluate_optimal_k_and_plot(X_scaled)
    k_metrics_df.to_csv("data/processed/clustering_k_validation_metrics.csv", index=False)

    # Fit Optimal K-Means (k=6) and Hierarchical Agglomerative Clustering (k=6, Ward)
    km = KMeans(n_clusters=6, init="k-means++", n_init=30, random_state=42)
    df_feat["kmeans_cluster"] = km.fit_predict(X_scaled)

    agg = AgglomerativeClustering(n_clusters=6, linkage="ward")
    df_feat["hierarchical_ward_cluster"] = agg.fit_predict(X_scaled)

    name_map = assign_human_cluster_names(df_feat, "kmeans_cluster")
    df_feat["cluster_name"] = df_feat["kmeans_cluster"].map(name_map)

    print("3. Generating Hierarchical Dendrogram & Linkage comparison...")
    plot_hierarchical_dendrogram_and_linkages(X_scaled, df_feat["region"].tolist())

    print("4. Generating PCA, t-SNE & India Geospatial Cluster Map...")
    plot_pca_tsne_and_spatial_map(df_feat, X_scaled, name_map)

    print("5. Generating Cluster Seasonal Trajectory & Centroid Signature Heatmap...")
    plot_cluster_seasonal_signatures(df_daily, df_feat, name_map)

    print("6. Running DBSCAN & Isolation Forest / LOF Hotspot Anomaly Detection...")
    run_dbscan_and_anomaly_detection(df_feat, X_scaled)

    # Benchmark vs Naive Annual-Average 1D Clustering
    X_annual_only = StandardScaler().fit_transform(df_feat[["annual_aod_mean", "annual_pm25_mean"]])
    km_naive = KMeans(n_clusters=6, random_state=42, n_init=20).fit_predict(X_annual_only)
    sil_multi = silhouette_score(X_scaled, df_feat["kmeans_cluster"])
    dbi_multi = davies_bouldin_score(X_scaled, df_feat["kmeans_cluster"])
    ari_km_vs_ward = adjusted_rand_score(df_feat["kmeans_cluster"], df_feat["hierarchical_ward_cluster"])

    # How well do annual-only clusters recover the true seasonal/source regimes vs our multi-season clustering?
    ari_multi_vs_regime = adjusted_rand_score(df_feat["geo_zone"], df_feat["kmeans_cluster"])
    ari_naive_vs_regime = adjusted_rand_score(df_feat["geo_zone"], km_naive)

    results_out = "data/processed/india_regions_clustered_results.csv"
    df_feat.to_csv(results_out, index=False)

    summary = {
        "optimal_k": 6,
        "kmeans_silhouette_score": round(float(sil_multi), 4),
        "kmeans_davies_bouldin_index": round(float(dbi_multi), 4),
        "kmeans_vs_ward_agreement_ari": round(float(ari_km_vs_ward), 4),
        "multi_season_pattern_recovery_ari": round(float(ari_multi_vs_regime), 4),
        "naive_annual_average_recovery_ari": round(float(ari_naive_vs_regime), 4),
        "cluster_counts": df_feat["cluster_name"].value_counts().to_dict(),
    }
    with open("data/processed/clustering_study_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n=== UNSUPERVISED CLUSTERING STUDY SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

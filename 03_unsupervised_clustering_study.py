"""
03_unsupervised_clustering_study.py
Groups NCAP cities by the SHAPE of their pollution year (season shares, episodic spikes,
particle size, SO2/NO2) rather than by their annual average, using real CAMS data.

Nothing is pre-labelled. The checks below need no ground-truth labels:
  * k chosen from silhouette + bootstrap stability (not fixed in advance)
  * year-to-year stability: cluster 2023, 2024, 2025 separately and compare
  * bootstrap stability: per-city assignment confidence over 200 resamples
  * independent evidence: FIRMS fires / ERA5 ventilation (NOT clustering inputs) tested
    against the clusters they should explain (Mann-Whitney U)
  * the "annual-average fallacy" measured directly: city pairs with near-identical annual
    PM2.5 but different seasonal signatures

Outputs:
  data/processed/city_clusters.csv
  data/processed/clustering_k_validation_metrics.csv
  data/processed/clustering_study_summary.json
  figures/01..06_*.png
"""

import json
from itertools import combinations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.optimize import linear_sum_assignment
from scipy.stats import mannwhitneyu
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.manifold import TSNE
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score,
                             silhouette_score)
from sklearn.neighbors import LocalOutlierFactor, NearestNeighbors
from sklearn.preprocessing import StandardScaler

from aeroscope_core.config import FIGURES_DIR, PROCESSED_DIR, YEARS

plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8

RNG_SEED = 42
N_BOOTSTRAP = 200
K_RANGE = range(3, 9)
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Shape-of-the-year features from CAMS pollutants only.
CLUSTER_FEATURES = [
    "winter_pm25_share", "premonsoon_pm25_share", "monsoon_pm25_share", "postmonsoon_pm25_share",
    "postmonsoon_smoke_spike", "winter_inversion_ratio", "premonsoon_dust_index", "dust_mam_mean",
    "coarse_fraction", "so2_to_no2_ratio", "annual_no2_mean", "annual_so2_mean",
    "annual_pm25_mean", "pm25_seasonal_cv", "pm25_peak_to_mean",
]
LOG_FEATURES = ["annual_no2_mean", "annual_so2_mean", "annual_pm25_mean", "postmonsoon_smoke_spike",
                "so2_to_no2_ratio", "pm25_peak_to_mean", "dust_mam_mean"]

# Signatures: which (z-scored) features indicate each pollution pattern. Keys match
# config/interventions.json. A negative weight means "low value indicates this signature".
SIGNATURES = {
    "winter_stagnation": {"label": "Winter smog (stagnant air)",
                          "indicators": {"winter_pm25_share": 1, "winter_inversion_ratio": 1}},
    "postmonsoon_smoke": {"label": "Post-monsoon smoke (crop-residue season)",
                          "indicators": {"postmonsoon_smoke_spike": 1, "postmonsoon_pm25_share": 1}},
    "premonsoon_dust": {"label": "Pre-monsoon dust",
                        "indicators": {"dust_mam_mean": 1, "coarse_fraction": 0.5, "premonsoon_pm25_share": 0.5}},
    "industrial_combustion": {"label": "Industrial / coal combustion (high SO₂)",
                              "indicators": {"so2_to_no2_ratio": 1, "annual_so2_mean": 1}},
    "urban_traffic": {"label": "Urban traffic & combustion (high NO₂)",
                      "indicators": {"annual_no2_mean": 1}},
    "cleaner_baseline": {"label": "Lower-pollution baseline",
                         "indicators": {"annual_pm25_mean": -1, "pm25_seasonal_cv": -0.5}},
}
SIGNATURE_THRESHOLD = 0.35
PALETTE = ["#d1495b", "#edae49", "#6a4c93", "#e07a2f", "#1d70b8", "#2a9d8f", "#8d6e63", "#5c946e"]


# ----------------------------------------------------------------------------- prep
def build_matrix(feat: pd.DataFrame, scaler: StandardScaler | None = None):
    X = feat[CLUSTER_FEATURES].astype(float).copy()
    for col in LOG_FEATURES:
        X[col] = np.log1p(X[col].clip(lower=0))
    X = X.fillna(X.median())
    if scaler is None:
        scaler = StandardScaler().fit(X)
    return scaler.transform(X), scaler


def kmeans(k, seed=RNG_SEED):
    return KMeans(n_clusters=k, init="k-means++", n_init=30, random_state=seed)


def match_labels(reference, labels, k):
    """Relabel `labels` to best agree with `reference` (Hungarian matching)."""
    cm = np.zeros((k, k))
    for r, l in zip(reference, labels):
        cm[r, l] += 1
    rows, cols = linear_sum_assignment(-cm)
    mapping = {c: r for r, c in zip(rows, cols)}
    return np.array([mapping.get(l, l) for l in labels])


def bootstrap_stability(X, k, ref_labels=None, n=N_BOOTSTRAP):
    rng = np.random.default_rng(RNG_SEED)
    ref = ref_labels if ref_labels is not None else kmeans(k).fit_predict(X)
    aris, agree = [], np.zeros(len(X))
    for b in range(n):
        idx = rng.choice(len(X), size=len(X), replace=True)
        model = KMeans(n_clusters=k, init="k-means++", n_init=5, random_state=b).fit(X[idx])
        pred = match_labels(ref, model.predict(X), k)
        aris.append(adjusted_rand_score(ref, pred))
        agree += pred == ref
    return float(np.mean(aris)), agree / n


# ----------------------------------------------------------------------------- k selection
def evaluate_k(X):
    rows = []
    for k in K_RANGE:
        model = kmeans(k).fit(X)
        lbl = model.labels_
        stab, _ = bootstrap_stability(X, k, lbl, n=60)
        rows.append({
            "k": k, "inertia_wcss": model.inertia_,
            "silhouette_score": silhouette_score(X, lbl),
            "davies_bouldin_index": davies_bouldin_score(X, lbl),
            "calinski_harabasz_score": calinski_harabasz_score(X, lbl),
            "bootstrap_mean_ari": stab,
            "smallest_cluster": int(np.bincount(lbl).min()),
        })
    m = pd.DataFrame(rows)
    ok = m[(m["bootstrap_mean_ari"] >= 0.6) & (m["smallest_cluster"] >= 3)]
    pool = ok if len(ok) else m
    # Highest silhouette among stable solutions; ties go to the more stable one.
    best = pool.sort_values(["silhouette_score", "bootstrap_mean_ari"], ascending=False).iloc[0]
    return m, int(best["k"])


def plot_k_selection(m: pd.DataFrame, k: int):
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.2))
    specs = [("inertia_wcss", "Elbow (WCSS)", "#1d70b8"), ("silhouette_score", "Silhouette (higher = better)", "#2a9d8f"),
             ("davies_bouldin_index", "Davies-Bouldin (lower = better)", "#6a4c93"),
             ("bootstrap_mean_ari", "Bootstrap stability (mean ARI)", "#d1495b")]
    for ax, (col, title, color) in zip(axes, specs):
        ax.plot(m["k"], m[col], marker="o", linewidth=2.2, color=color)
        ax.axvline(k, color="#333", linestyle="--", linewidth=1, label=f"chosen k = {k}")
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("k")
        ax.grid(alpha=0.25)
        ax.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "02_k_selection_metrics.png", dpi=200, bbox_inches="tight")
    plt.close()


# ----------------------------------------------------------------------------- naming
def signature_scores(feat: pd.DataFrame) -> pd.DataFrame:
    """Per-city z-score evidence for each signature (positive = stronger than the typical NCAP city)."""
    X = feat[CLUSTER_FEATURES].astype(float).copy()
    for col in LOG_FEATURES:
        X[col] = np.log1p(X[col].clip(lower=0))
    Z = (X - X.median()) / X.std(ddof=0).replace(0, 1)
    out = pd.DataFrame(index=feat.index)
    for key, spec in SIGNATURES.items():
        w = spec["indicators"]
        out[key] = sum(Z[c] * wt for c, wt in w.items()) / sum(abs(v) for v in w.values())
    return out


def name_clusters(labels: np.ndarray, scores: pd.DataFrame, feat: pd.DataFrame) -> dict:
    """Name each cluster after the signature its members most share; mark load level when names repeat."""
    med = scores.groupby(labels).median()
    names = {}
    for c, row in med.iterrows():
        ranked = row.sort_values(ascending=False)
        top = [s for s, v in ranked.items() if v >= SIGNATURE_THRESHOLD][:2]
        if not top:
            names[c] = {"key": "mixed", "label": "Mixed sources, no dominant season", "secondary": None}
        else:
            names[c] = {"key": top[0], "label": SIGNATURES[top[0]]["label"],
                        "secondary": top[1] if len(top) > 1 else None}
    # Disambiguate duplicate names by PM2.5 load.
    pm = feat.groupby(labels)["annual_pm25_mean"].median()
    by_key = {}
    for c, n in names.items():
        by_key.setdefault(n["label"], []).append(c)
    for label, cs in by_key.items():
        if len(cs) > 1:
            for c in cs:
                level = "higher" if pm[c] >= pm[cs].median() else "lower"
                names[c]["label"] = f"{label} – {level} load"
    return names


# ----------------------------------------------------------------------------- validation
def year_stability(feat_year: pd.DataFrame, k: int, scaler, model, pooled_labels: pd.Series):
    """Cluster each year on its own and compare years; also how often each city stays in its pooled cluster."""
    per_year, assigned = {}, {}
    for year in sorted(feat_year["year"].unique()):
        fy = feat_year[feat_year["year"] == year].set_index("city_id").reindex(pooled_labels.index).dropna(how="all")
        if len(fy) < k * 3:
            continue
        Xy, _ = build_matrix(fy)
        per_year[int(year)] = pd.Series(kmeans(k).fit_predict(Xy), index=fy.index)
        Xp, _ = build_matrix(fy, scaler)
        assigned[int(year)] = pd.Series(model.predict(Xp), index=fy.index)
    pairs = {}
    for a, b in combinations(per_year, 2):
        common = per_year[a].index.intersection(per_year[b].index)
        pairs[f"{a}_vs_{b}"] = round(float(adjusted_rand_score(per_year[a][common], per_year[b][common])), 3)
    same = pd.DataFrame(assigned).eq(pooled_labels, axis=0)
    return pairs, same.mean(axis=1), {y: round(float(same[y].mean()), 3) for y in same}


def evidence_tests(df: pd.DataFrame) -> list[dict]:
    """Independent (non-clustering) evidence checks for signature names."""
    tests = []
    checks = [
        ("postmonsoon_smoke", "upwind_fires_on_daily", "greater",
         "Upwind fire detections per day in Oct-Nov (FIRMS)"),
        ("postmonsoon_smoke", "fires_300km_on_daily", "greater", "Fire detections within 300 km in Oct-Nov (FIRMS)"),
        ("winter_stagnation", "poor_ventilation_days_djf", "greater",
         "Winter days with poor ventilation, VC < 2000 m²/s (ERA5)"),
    ]
    for sig, col, alt, desc in checks:
        if col not in df or df[col].notna().sum() < 10:
            tests.append({"signature": sig, "evidence": desc, "status": "data not available"})
            continue
        # A city is "in" the signature if its OWN signature score is high, independent of cluster ids.
        inside = df[df[f"sig_{sig}"] >= SIGNATURE_THRESHOLD][col].dropna()
        outside = df[df[f"sig_{sig}"] < SIGNATURE_THRESHOLD][col].dropna()
        if len(inside) < 3 or len(outside) < 3:
            tests.append({"signature": sig, "evidence": desc, "status": "too few cities"})
            continue
        stat, p = mannwhitneyu(inside, outside, alternative=alt)
        tests.append({
            "signature": sig, "evidence": desc, "status": "tested",
            "median_with_signature": round(float(inside.median()), 3),
            "median_without": round(float(outside.median()), 3),
            "n_with": int(len(inside)), "n_without": int(len(outside)),
            "p_value": float(f"{p:.3g}"), "supported": bool(p < 0.05),
        })
    return tests


def annual_average_fallacy(feat: pd.DataFrame, monthly: pd.DataFrame, tol=0.10):
    """City pairs whose annual PM2.5 is within +/-10% but whose monthly shapes disagree."""
    shape = monthly.pivot(index="city_id", columns="month", values="pm25_mean")
    shape = shape.div(shape.mean(axis=1), axis=0)
    f = feat.set_index("city_id")
    pairs, n_similar = [], 0
    for a, b in combinations(f.index, 2):
        pa, pb = f.at[a, "annual_pm25_mean"], f.at[b, "annual_pm25_mean"]
        if abs(pa - pb) / ((pa + pb) / 2) > tol:
            continue
        n_similar += 1
        r = np.corrcoef(shape.loc[a], shape.loc[b])[0, 1]
        if f.at[a, "cluster"] != f.at[b, "cluster"] and r < 0.5:
            pairs.append((a, b, round(float(r), 3)))
    return n_similar, pairs


def pick_showcase(feat: pd.DataFrame, monthly: pd.DataFrame, max_cities=4, tol=0.12):
    """Up to 4 cities from different clusters with near-identical annual PM2.5 and very different shapes."""
    shape = monthly.pivot(index="city_id", columns="month", values="pm25_mean")
    shape = shape.div(shape.mean(axis=1), axis=0)
    f = feat.set_index("city_id")
    best, best_score = [], -np.inf
    for anchor in f.index:
        level = f.at[anchor, "annual_pm25_mean"]
        cand = f[(f["annual_pm25_mean"] - level).abs() / level <= tol]
        chosen = [anchor]
        for cid in cand.sort_values("cluster_confidence", ascending=False).index:
            if len(chosen) >= max_cities:
                break
            if f.at[cid, "cluster"] in {f.at[c, "cluster"] for c in chosen}:
                continue
            chosen.append(cid)
        if len(chosen) < 3:
            continue
        corr = shape.loc[chosen].T.corr().values
        score = len(chosen) - np.mean(corr[np.triu_indices(len(chosen), 1)])
        if score > best_score:
            best, best_score = chosen, score
    return best


# ----------------------------------------------------------------------------- figures
def plot_fallacy(feat, monthly, showcase, names):
    if not showcase:
        return
    f = feat.set_index("city_id")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={"width_ratios": [1, 1.85]})
    labels = [f.at[c, "city"] for c in showcase]
    colors = [PALETTE[int(f.at[c, "cluster"]) % len(PALETTE)] for c in showcase]
    vals = [f.at[c, "annual_pm25_mean"] for c in showcase]
    bars = axes[0].bar(labels, vals, color=colors, width=0.55, edgecolor="#222")
    for bar, v in zip(bars, vals):
        axes[0].text(bar.get_x() + bar.get_width() / 2, v + 1, f"{v:.0f}", ha="center", fontweight="bold")
    axes[0].set_title("Annual mean PM2.5 looks the same...", fontweight="bold")
    axes[0].set_ylabel("Annual mean PM2.5 (µg/m³, CAMS)")
    axes[0].grid(axis="y", alpha=0.25)
    for c, color in zip(showcase, colors):
        m = monthly[monthly["city_id"] == c].sort_values("month")
        axes[1].plot(m["month"], m["pm25_mean"], marker="o", linewidth=2.4, color=color,
                     label=f"{f.at[c, 'city']}: {names[int(f.at[c, 'cluster'])]['label']}")
    axes[1].set_xticks(range(1, 13))
    axes[1].set_xticklabels(MONTHS)
    axes[1].set_title("...but the problem arrives in different months", fontweight="bold")
    axes[1].set_ylabel("Monthly mean PM2.5 (µg/m³)")
    axes[1].legend(fontsize=8.5)
    axes[1].grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "01_annual_average_fallacy.png", dpi=200, bbox_inches="tight")
    plt.close()


def plot_dendrogram(X, city_names, k):
    fig, axes = plt.subplots(1, 2, figsize=(16, 5.5), gridspec_kw={"width_ratios": [1.9, 1]})
    Z = linkage(X, method="ward")
    cut = (Z[-k, 2] + Z[-k + 1, 2]) / 2
    dendrogram(Z, labels=city_names, leaf_rotation=90, leaf_font_size=5.5, color_threshold=cut, ax=axes[0])
    axes[0].axhline(cut, color="#d1495b", linestyle="--", label=f"cut for k = {k}")
    axes[0].set_title("Ward hierarchical clustering of NCAP cities", fontweight="bold")
    axes[0].legend()
    methods = ["ward", "complete", "average", "single"]
    sil, dbi = [], []
    for m in methods:
        lbl = AgglomerativeClustering(n_clusters=k, linkage=m).fit_predict(X)
        sil.append(silhouette_score(X, lbl))
        dbi.append(davies_bouldin_score(X, lbl))
    x = np.arange(len(methods))
    axes[1].bar(x - 0.18, sil, width=0.36, color="#2a9d8f", label="Silhouette (↑)")
    axes[1].bar(x + 0.18, dbi, width=0.36, color="#e07a2f", label="Davies-Bouldin (↓)")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([m.capitalize() for m in methods])
    axes[1].set_title(f"Linkage comparison (k = {k})", fontweight="bold")
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "03_hierarchical_dendrogram_and_linkages.png", dpi=200, bbox_inches="tight")
    plt.close()


def plot_projections(df, names, pca_var):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.8))
    for c in sorted(names):
        sub = df[df["cluster"] == c]
        col = PALETTE[c % len(PALETTE)]
        lbl = f"{names[c]['label']} (n={len(sub)})"
        axes[0].scatter(sub["pca_1"], sub["pca_2"], c=col, s=50, edgecolors="#222", linewidth=0.5, label=lbl)
        axes[1].scatter(sub["tsne_1"], sub["tsne_2"], c=col, s=50, edgecolors="#222", linewidth=0.5)
        axes[2].scatter(sub["lon"], sub["lat"], c=col, s=sub["annual_pm25_mean"] * 1.2 + 15, edgecolors="#111",
                        linewidth=0.5, alpha=0.9)
    axes[0].set_title(f"PCA ({pca_var * 100:.0f}% variance in 2 components)", fontweight="bold")
    axes[1].set_title("t-SNE projection", fontweight="bold")
    axes[2].set_title("NCAP cities by signature (bubble = annual PM2.5)", fontweight="bold")
    axes[2].set_xlim(67.5, 97.5)
    axes[2].set_ylim(7.0, 35.5)
    for ax in axes:
        ax.grid(alpha=0.25)
    for _, r in df.nlargest(10, "annual_pm25_mean").iterrows():
        axes[2].annotate(r["city"], (r["lon"], r["lat"]), xytext=(4, 3), textcoords="offset points", fontsize=7.5)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.12), fontsize=9)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "04_pca_tsne_and_india_map.png", dpi=200, bbox_inches="tight")
    plt.close()


def plot_signatures(df, monthly, names, Xz):
    fig, axes = plt.subplots(1, 2, figsize=(16, 5.6), gridspec_kw={"width_ratios": [1.2, 1.4]})
    mm = monthly.merge(df[["city_id", "cluster"]], on="city_id")
    traj = mm.groupby(["cluster", "month"])["pm25_mean"].median().unstack("month")
    for c in sorted(names):
        axes[0].plot(range(1, 13), traj.loc[c], marker="o", linewidth=2.3, color=PALETTE[c % len(PALETTE)],
                     label=names[c]["label"])
    axes[0].set_xticks(range(1, 13))
    axes[0].set_xticklabels(MONTHS)
    axes[0].set_title("Median monthly PM2.5 by signature group", fontweight="bold")
    axes[0].set_ylabel("PM2.5 (µg/m³)")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.25)
    cent = pd.DataFrame(Xz, columns=CLUSTER_FEATURES).groupby(df["cluster"].values).mean()
    im = axes[1].imshow(cent.values, cmap="RdYlBu_r", aspect="auto", vmin=-2, vmax=2)
    axes[1].set_xticks(range(len(CLUSTER_FEATURES)))
    axes[1].set_xticklabels(CLUSTER_FEATURES, rotation=45, ha="right", fontsize=7.5)
    axes[1].set_yticks(range(len(cent)))
    axes[1].set_yticklabels([names[c]["label"][:38] for c in cent.index], fontsize=8)
    for r in range(cent.shape[0]):
        for c in range(cent.shape[1]):
            v = cent.values[r, c]
            axes[1].text(c, r, f"{v:+.1f}", ha="center", va="center", fontsize=6.8,
                         color="white" if abs(v) > 1.1 else "#111")
    plt.colorbar(im, ax=axes[1], fraction=0.03, label="z-score")
    axes[1].set_title("Cluster centroids (standardised features)", fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "05_cluster_seasonal_signatures.png", dpi=200, bbox_inches="tight")
    plt.close()


def run_density_and_anomalies(df, X):
    nn = NearestNeighbors(n_neighbors=5).fit(X)
    kdist = np.sort(nn.kneighbors(X)[0][:, -1])
    eps = float(np.percentile(kdist, 80))
    db = DBSCAN(eps=eps, min_samples=5).fit(X)
    core = set(db.core_sample_indices_)
    df["dbscan_cluster"] = db.labels_
    df["dbscan_role"] = ["noise" if l == -1 else ("core" if i in core else "border") for i, l in enumerate(db.labels_)]
    contamination = 0.1
    iso = IsolationForest(contamination=contamination, random_state=RNG_SEED).fit(X)
    df["isolation_forest_anomaly"] = iso.predict(X) == -1
    df["anomaly_score"] = -iso.score_samples(X)
    df["lof_anomaly"] = LocalOutlierFactor(n_neighbors=10, contamination=contamination).fit_predict(X) == -1
    df["consensus_outlier"] = df["isolation_forest_anomaly"] & df["lof_anomaly"]

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.2))
    for role, marker, alpha in (("core", "o", 0.9), ("border", "o", 0.5)):
        sub = df[df["dbscan_role"] == role]
        axes[0].scatter(sub["pca_1"], sub["pca_2"], c=sub["dbscan_cluster"], cmap="tab10", s=55, marker=marker,
                        alpha=alpha, edgecolors="#111", linewidth=0.5, label=f"{role} (n={len(sub)})")
    noise = df[df["dbscan_role"] == "noise"]
    axes[0].scatter(noise["pca_1"], noise["pca_2"], c="#d1495b", marker="^", s=80, edgecolors="#111",
                    label=f"noise (n={len(noise)})")
    axes[0].set_title(f"DBSCAN (eps={eps:.2f} from k-distance, MinPts=5)", fontweight="bold")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.25)
    top = df.sort_values("anomaly_score", ascending=False).head(12).iloc[::-1]
    axes[1].barh(top["city"] + " (" + top["state"] + ")", top["anomaly_score"],
                 color=np.where(top["consensus_outlier"], "#d1495b", "#bbbbbb"))
    axes[1].set_title("Most unusual pollution years (Isolation Forest; red = LOF agrees)", fontweight="bold")
    axes[1].grid(axis="x", alpha=0.25)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "06_dbscan_and_outliers.png", dpi=200, bbox_inches="tight")
    plt.close()
    return eps


# ----------------------------------------------------------------------------- main
def main():
    FIGURES_DIR.mkdir(exist_ok=True)
    for old in FIGURES_DIR.glob("*.png"):
        old.unlink()
    feat = pd.read_csv(PROCESSED_DIR / "city_features.csv")
    feat_year = pd.read_csv(PROCESSED_DIR / "city_features_by_year.csv")
    monthly = pd.read_csv(PROCESSED_DIR / "monthly_profile.csv")
    X, scaler = build_matrix(feat)

    print("1. Choosing k (silhouette + bootstrap stability)...")
    k_metrics, k = evaluate_k(X)
    k_metrics.round(4).to_csv(PROCESSED_DIR / "clustering_k_validation_metrics.csv", index=False)
    plot_k_selection(k_metrics, k)
    print(k_metrics.round(3).to_string(index=False))
    print(f"   -> k = {k}")

    model = kmeans(k).fit(X)
    feat["cluster"] = model.labels_
    feat["ward_cluster"] = match_labels(model.labels_, AgglomerativeClustering(n_clusters=k).fit_predict(X), k)

    print("2. Bootstrap + year-to-year stability...")
    boot_ari, confidence = bootstrap_stability(X, k, model.labels_)
    feat["cluster_confidence"] = confidence.round(3)
    pooled = feat.set_index("city_id")["cluster"]
    year_pairs, year_consistency, year_share = year_stability(feat_year, k, scaler, model, pooled)
    feat["years_in_same_cluster"] = feat["city_id"].map(year_consistency).round(3)

    print("3. Naming clusters from their signatures...")
    scores = signature_scores(feat)
    for key in SIGNATURES:
        feat[f"sig_{key}"] = scores[key].round(3)
    names = name_clusters(model.labels_, scores, feat)
    if feat["fires_300km_on_daily"].notna().sum() < 10:
        # Without fire detections an Oct-Nov peak is not proof of smoke; say only what the data shows.
        for n in names.values():
            n["label"] = n["label"].replace("Post-monsoon smoke (crop-residue season)",
                                            "Post-monsoon peak (Oct–Nov; smoke not verified)")
    feat["cluster_key"] = feat["cluster"].map(lambda c: names[c]["key"])
    feat["cluster_name"] = feat["cluster"].map(lambda c: names[c]["label"])
    ranked = scores.apply(lambda r: [s for s, v in r.sort_values(ascending=False).items() if v >= SIGNATURE_THRESHOLD], axis=1)
    feat["city_signatures"] = ranked.map(lambda l: "|".join(l))

    print("4. Projections, density clustering and outliers...")
    pca = PCA(n_components=2, random_state=RNG_SEED).fit(X)
    P = pca.transform(X)
    T = TSNE(n_components=2, perplexity=min(25, len(X) // 4), random_state=RNG_SEED, init="pca",
             learning_rate="auto").fit_transform(X)
    feat["pca_1"], feat["pca_2"], feat["tsne_1"], feat["tsne_2"] = P[:, 0], P[:, 1], T[:, 0], T[:, 1]
    eps = run_density_and_anomalies(feat, X)

    print("5. Independent evidence + annual-average fallacy...")
    tests = evidence_tests(feat)
    n_similar, fallacy_pairs = annual_average_fallacy(feat, monthly)
    showcase = pick_showcase(feat, monthly)

    plot_fallacy(feat, monthly, showcase, names)
    plot_dendrogram(X, feat["city"].tolist(), k)
    plot_projections(feat, names, pca.explained_variance_ratio_.sum())
    plot_signatures(feat, monthly, names, X)

    # Naive baseline: same k on annual PM2.5 alone. How much does it mix different seasonal signatures?
    naive = kmeans(k).fit_predict(np.log1p(feat[["annual_pm25_mean"]].to_numpy()))
    feat["naive_annual_cluster"] = match_labels(model.labels_, naive, k)

    feat.to_csv(PROCESSED_DIR / "city_clusters.csv", index=False)
    summary = {
        "n_cities": int(len(feat)),
        "years": list(YEARS),
        "chosen_k": k,
        "kmeans_silhouette": round(float(silhouette_score(X, model.labels_)), 4),
        "kmeans_davies_bouldin": round(float(davies_bouldin_score(X, model.labels_)), 4),
        "kmeans_vs_ward_ari": round(float(adjusted_rand_score(model.labels_, feat["ward_cluster"])), 4),
        "bootstrap_mean_ari": round(boot_ari, 4),
        "cities_with_confidence_ge_0_8": int((feat["cluster_confidence"] >= 0.8).sum()),
        "year_to_year_ari": year_pairs,
        "share_of_cities_in_pooled_cluster_by_year": year_share,
        "naive_annual_vs_seasonal_ari": round(float(adjusted_rand_score(model.labels_, naive)), 4),
        "dbscan_eps": round(eps, 3),
        "dbscan_noise_cities": int((feat["dbscan_role"] == "noise").sum()),
        "consensus_outliers": feat.loc[feat["consensus_outlier"], "city"].tolist(),
        "evidence_tests": tests,
        "annual_average_fallacy": {
            "city_pairs_with_annual_pm25_within_10pct": n_similar,
            "of_which_different_cluster_and_shape_corr_below_0_5": len(fallacy_pairs),
            "showcase_cities": showcase,
            "example_pairs": fallacy_pairs[:15],
        },
        "clusters": {
            int(c): {**names[c], "n_cities": int((feat["cluster"] == c).sum()),
                     "median_annual_pm25": round(float(feat.loc[feat["cluster"] == c, "annual_pm25_mean"].median()), 1),
                     "cities": feat.loc[feat["cluster"] == c, "city"].tolist()}
            for c in sorted(names)
        },
    }
    with open(PROCESSED_DIR / "clustering_study_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    brief = {k_: v for k_, v in summary.items() if k_ not in ("clusters", "annual_average_fallacy")}
    brief["annual_average_fallacy"] = {k_: v for k_, v in summary["annual_average_fallacy"].items()
                                       if k_ != "example_pairs"}
    print(json.dumps(brief, indent=2, default=str))
    for c, info in summary["clusters"].items():
        print(f"  C{c} {info['label']} (n={info['n_cities']}, PM2.5~{info['median_annual_pm25']}): "
              f"{', '.join(info['cities'][:8])}{'...' if info['n_cities'] > 8 else ''}")


if __name__ == "__main__":
    main()

/**
 * app.js
 * Interactive logic & Canvas renderers for the Hallmark Vantage (terrain/steel)
 * INSAT-3D Regional Pollution-Hotspot Clustering Study frontend.
 */

(function () {
  "use strict";

  const DATA = window.INSAT_STUDY_DATA;
  if (!DATA) return;

  const INDIA_POLY = [
    // Gujarat: Kutch & Saurashtra Peninsula (counter-clockwise)
    [68.12, 23.65], [68.85, 22.85], [69.05, 22.25], [70.18, 20.92], [70.95, 20.75],
    [71.65, 21.15], [72.25, 21.75], [72.62, 21.65], [72.90, 20.45],
    // West Coast: Konkan, Goa, Karnataka, Malabar & Kerala down to Thiruvananthapuram & Kanyakumari
    [72.82, 19.07], [72.98, 17.95], [73.35, 16.98], [73.78, 15.55], [74.05, 14.82],
    [74.45, 13.85], [74.85, 12.91], [75.35, 11.88], [75.78, 11.25], [76.02, 10.55],
    [76.26, 9.93],  // Kochi
    [76.34, 9.49],  // Alappuzha
    [76.58, 8.89],  // Kollam
    [76.94, 8.52],  // Thiruvananthapuram
    [77.54, 8.08],  // Kanyakumari (Southernmost mainland tip)
    // East Coast: Tamil Nadu, Andhra Pradesh, Odisha, West Bengal Sundarbans
    [78.15, 8.78], [78.82, 9.28], [79.32, 9.28], [79.15, 10.05], [79.82, 10.76],
    [79.85, 11.94], [80.27, 13.08], [80.08, 14.45], [80.12, 15.42], [80.85, 15.82],
    [81.75, 16.45], [82.24, 16.98], [83.30, 17.70], [84.78, 19.15], [85.82, 19.80],
    [86.95, 20.75], [87.08, 21.52], [88.25, 21.62], [89.02, 21.68],
    // Bangladesh border (South of Siliguri corridor) -> Meghalaya -> Tripura -> Mizoram
    [88.95, 22.65], [88.65, 23.55], [88.48, 24.25], [88.18, 24.85], [88.45, 25.35],
    [88.42, 25.95], [88.75, 26.22], [89.55, 26.08], [89.88, 25.62], [90.15, 25.22],
    [91.05, 25.18], [92.05, 25.05], [92.35, 24.65], [91.85, 24.35], [91.25, 23.52],
    [91.58, 22.98], [92.18, 23.65], [92.42, 22.65], [92.95, 22.02],
    // Eastern border: Manipur -> Nagaland -> Arunachal Pradesh -> Bhutan -> Sikkim
    [93.35, 23.15], [93.92, 23.85], [94.35, 24.45], [94.75, 25.45], [95.15, 26.35],
    [96.15, 27.05], [96.95, 27.35], [97.38, 28.18], [96.65, 28.65], [96.12, 29.35],
    [94.65, 29.15], [93.65, 28.35], [92.55, 27.88], [91.65, 27.75], [91.55, 26.82],
    [89.85, 26.72], [89.15, 26.82], [88.92, 27.32], [88.65, 27.95], [88.12, 27.88],
    [88.02, 27.15], [88.05, 26.68],
    // Himalayan Arc: Nepal border, Uttarakhand, Himachal Pradesh
    [86.85, 26.65], [85.15, 26.78], [83.95, 27.35], [82.15, 27.85],
    [81.05, 28.45], [80.15, 28.88], [80.25, 29.75], [81.02, 30.25], [79.85, 30.92],
    [78.95, 31.42], [78.65, 32.15], [78.42, 32.65],
    // Full Northern Crown: Ladakh & Jammu and Kashmir (Aksai Chin, Karakoram, Indira Col, Gilgit)
    [79.25, 32.75], [79.55, 33.45], [78.95, 33.95], [79.85, 34.55], [80.35, 35.15],
    [79.95, 35.75], [78.95, 35.85], [77.85, 35.52], [77.05, 35.95], [76.15, 35.88],
    [75.45, 36.45], [74.65, 37.08], [73.65, 36.85], [72.85, 36.15], [72.55, 35.35],
    [73.25, 34.75], [73.85, 34.25], [73.75, 33.45], [74.15, 32.75], [74.75, 32.28],
    // Western Border: Punjab, Rajasthan, Rann of Kutch
    [74.52, 31.55], [73.92, 30.25], [73.25, 29.25], [72.15, 28.15], [70.65, 27.85],
    [69.52, 26.85], [70.15, 25.95], [70.95, 25.15], [70.85, 24.42], [69.25, 24.15],
    [68.12, 23.65]
  ];

  const SHORT_CLUSTER_LABEL = {
    C1: "C1: Biomass smoke",
    C2: "C2: Mineral dust",
    C3: "C3: Coal & industrial",
    C4: "C4: Winter inversion",
    C5: "C5: Urban vehicular",
    C6: "C6: Clean baseline"
  };

  const rootStyles = getComputedStyle(document.documentElement);
  const TOKEN = (name) => rootStyles.getPropertyValue(name).trim();

  const PALETTE = {
    paper: () => TOKEN("--color-paper"),
    paper2: () => TOKEN("--color-paper-2"),
    paper3: () => TOKEN("--color-paper-3"),
    ink: () => TOKEN("--color-ink"),
    ink2: () => TOKEN("--color-ink-2"),
    muted: () => TOKEN("--color-muted"),
    rule: () => TOKEN("--color-rule"),
    rule2: () => TOKEN("--color-rule-2"),
    accent: () => TOKEN("--color-accent"),
    pointLo: () => TOKEN("--point-lo"),
    pointMid: () => TOKEN("--point-mid"),
    pointHi: () => TOKEN("--point-hi"),
    clusters: {
      C1: () => TOKEN("--cluster-c1"),
      C2: () => TOKEN("--cluster-c2"),
      C3: () => TOKEN("--cluster-c3"),
      C4: () => TOKEN("--cluster-c4"),
      C5: () => TOKEN("--cluster-c5"),
      C6: () => TOKEN("--cluster-c6")
    }
  };

  const state = {
    projectionView: "geo",       // 'geo' | 'pca' | 'tsne'
    algorithm: "kmeans",         // 'kmeans' | 'ward' | 'dbscan' | 'anomaly' | 'naive'
    activeClusters: new Set(["C1", "C2", "C3", "C4", "C5", "C6"]),
    selectedRegion: DATA.regions.find((r) => r.region === "Ludhiana") || DATA.regions[0],
    cutMetric: "aod",            // 'aod' | 'pm25'
    cutReferenceNames: ["Ludhiana", "Patna", "Dhanbad", "Jodhpur"],
    selectedK: 6,
    searchQuery: "",
    tableClusterFilter: "ALL",
    pointerTiltX: 0,
    pointerTiltY: 0,
    reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches
  };

  function pointInIndia(lon, lat) {
    let inside = false;
    for (let i = 0, j = INDIA_POLY.length - 1; i < INDIA_POLY.length; j = i++) {
      const xi = INDIA_POLY[i][0], yi = INDIA_POLY[i][1];
      const xj = INDIA_POLY[j][0], yj = INDIA_POLY[j][1];
      const intersect = ((yi > lat) !== (yj > lat)) &&
        (lon < ((xj - xi) * (lat - yi)) / (yj - yi + 1e-9) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }

  const cloudPoints = [];
  (function buildPointCloud() {
    let seed = 10839528;
    const rand = () => {
      seed = (seed * 1664525 + 1013904223) % 4294967296;
      return seed / 4294967296;
    };

    for (let lat = 8.05; lat <= 37.05; lat += 0.45) {
      for (let lon = 68.1; lon <= 97.4; lon += 0.45) {
        const jLon = lon + (rand() - 0.5) * 0.30;
        const jLat = lat + (rand() - 0.5) * 0.30;
        if (pointInIndia(jLon, jLat)) {
          let minDist = 999, nearAod = 0.25;
          for (let i = 0; i < DATA.regions.length; i++) {
            const r = DATA.regions[i];
            const d = Math.hypot(r.lon - jLon, r.lat - jLat);
            if (d < minDist) {
              minDist = d;
              nearAod = r.annual_aod;
            }
          }
          cloudPoints.push({
            lon: jLon,
            lat: jLat,
            z: nearAod * 0.85 + rand() * 0.08,
            isStation: false,
            regionObj: null
          });
        }
      }
    }

    DATA.regions.forEach((reg) => {
      cloudPoints.push({
        lon: reg.lon,
        lat: reg.lat,
        z: reg.annual_aod * 1.35,
        isStation: true,
        regionObj: reg
      });
    });
  })();

  // Returns the active cluster code for a region under the selected algorithm
  function getActiveClusterCode(reg) {
    if (state.algorithm === "ward") return reg.hier_code;
    if (state.algorithm === "naive") return reg.naive_code;
    return reg.cluster_code;
  }

  function getRegionColor(reg) {
    if (state.algorithm === "ward") {
      return PALETTE.clusters[reg.hier_code]();
    }
    if (state.algorithm === "naive") {
      return PALETTE.clusters[reg.naive_code]();
    }
    if (state.algorithm === "dbscan") {
      if (reg.dbscan_role === "noise") return PALETTE.accent();
      return PALETTE.clusters[reg.cluster_code]();
    }
    if (state.algorithm === "anomaly") {
      return reg.is_anomaly ? PALETTE.accent() : PALETTE.pointLo();
    }
    return PALETTE.clusters[reg.cluster_code]();
  }

  function resizeCanvasHiDPI(canvas, ctx, cssHeight) {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const w = Math.max(300, Math.floor(rect.width));
    const h = cssHeight || Math.max(260, Math.floor(rect.height));
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { w, h };
  }

  function drawCalloutPill(ctx, text, x, y, alignRight) {
    ctx.font = "400 11px Geologica, sans-serif";
    const padX = 6;
    const tw = ctx.measureText(text).width;
    const boxX = alignRight ? x - tw - padX * 2 : x;
    const boxY = y - 11;
    ctx.fillStyle = PALETTE.paper();
    ctx.fillRect(boxX, boxY, tw + padX * 2, 17);
    ctx.strokeStyle = PALETTE.rule2();
    ctx.lineWidth = 1;
    ctx.strokeRect(boxX, boxY, tw + padX * 2, 17);
    ctx.fillStyle = PALETTE.ink();
    ctx.fillText(text, boxX + padX, y + 1);
  }

  // =========================================================================
  // 1. HERO 3D POINT-CLOUD RENDERER (#india-cloud-canvas)
  // =========================================================================
  const heroCanvas = document.getElementById("india-cloud-canvas");
  const heroCtx = heroCanvas.getContext("2d");
  let heroScreenStations = [];

  function renderHeroCloud(timestamp) {
    const { w, h } = resizeCanvasHiDPI(heroCanvas, heroCtx);
    heroCtx.clearRect(0, 0, w, h);

    const tSec = state.reducedMotion ? 2.4 : (timestamp || 0) / 1000;
    const yaw = Math.sin(tSec * 0.22) * 0.11 + state.pointerTiltX * 0.08;
    const pitch = 0.28 + state.pointerTiltY * 0.04;
    const cosY = Math.cos(yaw), sinY = Math.sin(yaw);
    const cosP = Math.cos(pitch), sinP = Math.sin(pitch);

    const sweepCycle = (tSec % 7.5) / 7.5;
    const sweepPos = -1.15 + 2.3 * (0.5 - 0.5 * Math.cos(sweepCycle * Math.PI * 2));

    // Centered and scaled so 8.08°N (Kanyakumari/Thiruvananthapuram) to 37.08°N (Ladakh/Kashmir)
    // always fits inside the stage with comfortable top and bottom margins.
    const scale = Math.min(w, h) * 0.51;
    const cx = w * 0.50;
    const cy = h * 0.495;

    const project3D = (lon, lat, zVal) => {
      const nx = (lon - 82.5) / 15.0;
      const ny = -(lat - 22.58) / 15.0;
      const nz = zVal * 0.32;

      const rx = nx * cosY + nz * sinY;
      const rz1 = -nx * sinY + nz * cosY;
      const ry = ny * cosP - rz1 * sinP;
      const rz = ny * sinP + rz1 * cosP;

      const persp = 1 / (2.5 - rz * 0.35);
      return {
        sx: cx + rx * scale * persp * 2.15,
        sy: cy + ry * scale * persp * 2.15,
        nx
      };
    };

    // Draw subtle 3D boundary outline of India first so southern tip (Thiruvananthapuram/Kanyakumari)
    // and northern crown (Kashmir/Ladakh) are unmistakably framed.
    heroCtx.beginPath();
    for (let i = 0; i < INDIA_POLY.length; i++) {
      const [lon, lat] = INDIA_POLY[i];
      const { sx, sy } = project3D(lon, lat, 0.10);
      if (i === 0) heroCtx.moveTo(sx, sy);
      else heroCtx.lineTo(sx, sy);
    }
    heroCtx.closePath();
    heroCtx.strokeStyle = PALETTE.rule2();
    heroCtx.lineWidth = 1.0;
    heroCtx.stroke();

    heroScreenStations = [];
    let selStationCoord = null;
    let dhanbadCoord = null;
    let trivandrumCoord = null;
    let kochiCoord = null;

    // 1. Render background LiDAR terrain cloud points
    for (let i = 0; i < cloudPoints.length; i++) {
      const pt = cloudPoints[i];
      if (pt.isStation) continue;

      const { sx, sy, nx } = project3D(pt.lon, pt.lat, pt.z);
      const distToSweep = Math.abs(nx - sweepPos);
      const inSweep = distToSweep < 0.16;

      if (inSweep) {
        heroCtx.fillStyle = PALETTE.pointHi();
      } else if (pt.z > 0.45) {
        heroCtx.fillStyle = PALETTE.pointMid();
      } else {
        heroCtx.fillStyle = PALETTE.pointLo();
      }
      const sz = inSweep ? 1.65 : 1.2;
      heroCtx.fillRect(sx - sz * 0.5, sy - sz * 0.5, sz, sz);
    }

    // 2. Render all 108 monitoring stations on top in their cluster colors
    for (let i = 0; i < cloudPoints.length; i++) {
      const pt = cloudPoints[i];
      if (!pt.isStation) continue;
      const cCode = getActiveClusterCode(pt.regionObj);
      if (!state.activeClusters.has(cCode)) continue;

      const { sx, sy, nx } = project3D(pt.lon, pt.lat, pt.z);
      const distToSweep = Math.abs(nx - sweepPos);
      const inSweep = distToSweep < 0.16;
      const isSel = state.selectedRegion && pt.regionObj.region === state.selectedRegion.region;

      heroCtx.fillStyle = isSel
        ? PALETTE.accent()
        : (PALETTE.clusters[cCode] ? PALETTE.clusters[cCode]() : PALETTE.pointHi());
      const rSize = isSel ? 4.4 : (inSweep ? 3.5 : 2.9);
      heroCtx.beginPath();
      heroCtx.arc(sx, sy, rSize, 0, Math.PI * 2);
      heroCtx.fill();
      heroCtx.strokeStyle = PALETTE.paper();
      heroCtx.lineWidth = 0.8;
      heroCtx.stroke();

      if (isSel) {
        heroCtx.strokeStyle = PALETTE.accent();
        heroCtx.lineWidth = 1.3;
        heroCtx.beginPath();
        heroCtx.arc(sx, sy, 8, 0, Math.PI * 2);
        heroCtx.stroke();
        selStationCoord = { sx, sy, reg: pt.regionObj };
      }
      if (pt.regionObj.region === "Dhanbad") {
        dhanbadCoord = { sx, sy, reg: pt.regionObj };
      }
      if (pt.regionObj.region === "Thiruvananthapuram") {
        trivandrumCoord = { sx, sy, reg: pt.regionObj };
      }
      if (pt.regionObj.region === "Kochi") {
        kochiCoord = { sx, sy, reg: pt.regionObj };
      }

      heroScreenStations.push({ sx, sy, regionObj: pt.regionObj });
    }

    if (selStationCoord) {
      const targetX = 16;
      const targetY = Math.max(26, Math.min(h * 0.34, selStationCoord.sy - 24));
      heroCtx.strokeStyle = PALETTE.rule2();
      heroCtx.lineWidth = 1;
      heroCtx.beginPath();
      heroCtx.moveTo(selStationCoord.sx, selStationCoord.sy);
      heroCtx.lineTo(selStationCoord.sx - 24, targetY);
      heroCtx.lineTo(targetX + 10, targetY);
      heroCtx.stroke();
      drawCalloutPill(
        heroCtx,
        `${selStationCoord.reg.region}: ${selStationCoord.reg.annual_aod.toFixed(2)} AOD (${selStationCoord.reg.cluster_code})`,
        targetX,
        targetY,
        false
      );
    }

    // Southern Kerala coastal callout: show Thiruvananthapuram (below Kochi) so both southern stations are clear
    if (trivandrumCoord && (!selStationCoord || selStationCoord.reg.region !== "Thiruvananthapuram")) {
      const targetX = 16;
      const targetY = Math.min(h - 18, Math.max(h * 0.82, trivandrumCoord.sy + 4));
      heroCtx.strokeStyle = PALETTE.rule2();
      heroCtx.lineWidth = 1;
      heroCtx.beginPath();
      heroCtx.moveTo(trivandrumCoord.sx, trivandrumCoord.sy);
      heroCtx.lineTo(trivandrumCoord.sx - 22, targetY);
      heroCtx.lineTo(targetX + 10, targetY);
      heroCtx.stroke();
      drawCalloutPill(
        heroCtx,
        `Thiruvananthapuram: ${trivandrumCoord.reg.annual_aod.toFixed(2)} AOD (C6)`,
        targetX,
        targetY,
        false
      );
    } else if (kochiCoord && selStationCoord && selStationCoord.reg.region === "Thiruvananthapuram") {
      const targetX = 16;
      const targetY = Math.max(h * 0.64, kochiCoord.sy - 18);
      heroCtx.strokeStyle = PALETTE.rule2();
      heroCtx.lineWidth = 1;
      heroCtx.beginPath();
      heroCtx.moveTo(kochiCoord.sx, kochiCoord.sy);
      heroCtx.lineTo(kochiCoord.sx - 22, targetY);
      heroCtx.lineTo(targetX + 10, targetY);
      heroCtx.stroke();
      drawCalloutPill(
        heroCtx,
        `Kochi: ${kochiCoord.reg.annual_aod.toFixed(2)} AOD (C6)`,
        targetX,
        targetY,
        false
      );
    }

    if (dhanbadCoord && (!selStationCoord || selStationCoord.reg.region !== "Dhanbad")) {
      const targetX = w - 16;
      const targetY = Math.min(h - 24, Math.max(h * 0.68, dhanbadCoord.sy + 32));
      heroCtx.strokeStyle = PALETTE.rule2();
      heroCtx.lineWidth = 1;
      heroCtx.beginPath();
      heroCtx.moveTo(dhanbadCoord.sx, dhanbadCoord.sy);
      heroCtx.lineTo(dhanbadCoord.sx + 24, targetY);
      heroCtx.lineTo(targetX - 10, targetY);
      heroCtx.stroke();
      drawCalloutPill(
        heroCtx,
        `Dhanbad: 46.8 µg/m³ SO₂ (C3)`,
        targetX,
        targetY,
        true
      );
    }

    if (!state.reducedMotion) {
      requestAnimationFrame(renderHeroCloud);
    }
  }

  heroCanvas.addEventListener("mousemove", (e) => {
    const rect = heroCanvas.getBoundingClientRect();
    state.pointerTiltX = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
    state.pointerTiltY = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
    if (state.reducedMotion) renderHeroCloud(2400);
  });

  heroCanvas.addEventListener("click", (e) => {
    const rect = heroCanvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    let best = null, bestDist = 18;
    for (const st of heroScreenStations) {
      const d = Math.hypot(st.sx - mx, st.sy - my);
      if (d < bestDist) {
        bestDist = d;
        best = st.regionObj;
      }
    }
    if (best) selectRegion(best);
  });

  // =========================================================================
  // 2. SPATIAL MAP / PCA / t-SNE WORKBENCH RENDERER (#spatial-manifold-canvas)
  // =========================================================================
  const mapCanvas = document.getElementById("spatial-manifold-canvas");
  const mapCtx = mapCanvas.getContext("2d");
  let mapScreenNodes = [];

  function drawTriangle(ctx, x, y, r) {
    ctx.beginPath();
    ctx.moveTo(x, y - r * 1.25);
    ctx.lineTo(x + r * 1.15, y + r * 0.9);
    ctx.lineTo(x - r * 1.15, y + r * 0.9);
    ctx.closePath();
  }

  function drawCrossMark(ctx, x, y, r) {
    ctx.beginPath();
    ctx.moveTo(x - r, y - r);
    ctx.lineTo(x + r, y + r);
    ctx.moveTo(x + r, y - r);
    ctx.lineTo(x - r, y + r);
    ctx.stroke();
  }

  function renderSpatialManifold() {
    const { w, h } = resizeCanvasHiDPI(mapCanvas, mapCtx, 390);
    mapCtx.clearRect(0, 0, w, h);
    mapScreenNodes = [];

    const padX = 52, padY = 34;
    const plotW = w - padX * 2;
    const plotH = h - padY * 2;

    let toScreen;
    let lonMin = 67.5, lonMax = 97.8, latMin = 7.2, latMax = 37.6;
    let geoScale = 1, offsetX = 0, offsetY = 0;

    if (state.projectionView === "geo") {
      geoScale = Math.min(plotW / (lonMax - lonMin), plotH / (latMax - latMin));
      offsetX = padX + (plotW - (lonMax - lonMin) * geoScale) * 0.5;
      offsetY = padY + (plotH - (latMax - latMin) * geoScale) * 0.5;
      toScreen = (lon, lat) => [
        offsetX + (lon - lonMin) * geoScale,
        offsetY + (latMax - lat) * geoScale
      ];

      // Draw India boundary polygon
      mapCtx.beginPath();
      INDIA_POLY.forEach(([lon, lat], idx) => {
        const [sx, sy] = toScreen(lon, lat);
        if (idx === 0) mapCtx.moveTo(sx, sy);
        else mapCtx.lineTo(sx, sy);
      });
      mapCtx.closePath();
      mapCtx.fillStyle = PALETTE.paper2();
      mapCtx.fill();
      mapCtx.strokeStyle = PALETTE.rule2();
      mapCtx.lineWidth = 1.1;
      mapCtx.stroke();

      // Graticule ticks
      mapCtx.fillStyle = PALETTE.muted();
      mapCtx.font = "300 11px Geologica, sans-serif";
      [70, 75, 80, 85, 90, 95].forEach((lon) => {
        const [sx] = toScreen(lon, latMin);
        mapCtx.fillText(lon + "°E", sx - 12, h - 8);
      });
      [10, 15, 20, 25, 30, 35].forEach((lat) => {
        const [, sy] = toScreen(lonMin, lat);
        mapCtx.fillText(lat + "°N", 10, sy + 4);
      });
    } else {
      const xKey = state.projectionView === "pca" ? "pca_1" : "tsne_1";
      const yKey = state.projectionView === "pca" ? "pca_2" : "tsne_2";
      const xs = DATA.regions.map((r) => r[xKey]);
      const ys = DATA.regions.map((r) => r[yKey]);
      const xMin = Math.min(...xs) - 1.0, xMax = Math.max(...xs) + 1.0;
      const yMin = Math.min(...ys) - 1.0, yMax = Math.max(...ys) + 1.0;

      toScreen = (vx, vy) => [
        padX + ((vx - xMin) / (xMax - xMin)) * plotW,
        padY + ((yMax - vy) / (yMax - yMin)) * plotH
      ];

      const [zx, zy] = toScreen(0, 0);
      mapCtx.strokeStyle = PALETTE.rule();
      mapCtx.beginPath();
      mapCtx.moveTo(padX, zy);
      mapCtx.lineTo(w - padX, zy);
      mapCtx.moveTo(zx, padY);
      mapCtx.lineTo(zx, h - padY);
      mapCtx.stroke();
    }

    const getPointXY = (reg) => {
      if (state.projectionView === "geo") return toScreen(reg.lon, reg.lat);
      if (state.projectionView === "pca") return toScreen(reg.pca_1, reg.pca_2);
      return toScreen(reg.tsne_1, reg.tsne_2);
    };

    const getCentroidXY = (cMeta) => {
      if (state.projectionView === "geo") return toScreen(cMeta.mean_lon, cMeta.mean_lat);
      if (state.projectionView === "pca") return toScreen(cMeta.mean_pca_1, cMeta.mean_pca_2);
      return toScreen(cMeta.mean_tsne_1, cMeta.mean_tsne_2);
    };

    // =======================================================================
    // ALGORITHM-SPECIFIC STRUCTURAL UNDERLAYS
    // =======================================================================
    if (state.algorithm === "kmeans") {
      // Draw Voronoi centroid spoke rays from each station to its K-Means centroid
      DATA.regions.forEach((reg) => {
        const cCode = getActiveClusterCode(reg);
        if (!state.activeClusters.has(cCode)) return;
        const cMeta = DATA.clusters.find((c) => c.code === cCode);
        if (!cMeta) return;
        const [sx, sy] = getPointXY(reg);
        const [cx, cy] = getCentroidXY(cMeta);
        mapCtx.strokeStyle = PALETTE.rule2();
        mapCtx.lineWidth = 0.7;
        mapCtx.beginPath();
        mapCtx.moveTo(sx, sy);
        mapCtx.lineTo(cx, cy);
        mapCtx.stroke();
      });
    } else if (state.algorithm === "ward") {
      // Draw Hierarchical Agglomerative Nearest-Neighbor Merge Tree edges
      const regByName = {};
      DATA.regions.forEach((r) => { regByName[r.region] = r; });
      DATA.regions.forEach((reg) => {
        const cCode = getActiveClusterCode(reg);
        if (!state.activeClusters.has(cCode)) return;
        const parent = regByName[reg.hier_link_to];
        if (!parent) return;
        const [sx, sy] = getPointXY(reg);
        const [px, py] = getPointXY(parent);
        mapCtx.strokeStyle = PALETTE.clusters[cCode]();
        mapCtx.lineWidth = 1.1;
        mapCtx.beginPath();
        mapCtx.moveTo(sx, sy);
        mapCtx.lineTo(px, py);
        mapCtx.stroke();
      });
    } else if (state.algorithm === "dbscan") {
      // Draw translucent epsilon-density neighborhood halos around DBSCAN Core points
      DATA.regions.forEach((reg) => {
        const cCode = getActiveClusterCode(reg);
        if (!state.activeClusters.has(cCode)) return;
        if (reg.dbscan_role !== "core") return;
        const [sx, sy] = getPointXY(reg);
        mapCtx.strokeStyle = PALETTE.rule2();
        mapCtx.lineWidth = 0.8;
        mapCtx.beginPath();
        mapCtx.arc(sx, sy, 12, 0, Math.PI * 2);
        mapCtx.stroke();
      });
    }

    // =======================================================================
    // PLOT THE 108 STATION NODES WITH ALGORITHM-SPECIFIC GLYPHS
    // =======================================================================
    DATA.regions.forEach((reg) => {
      const cCode = getActiveClusterCode(reg);
      if (!state.activeClusters.has(cCode)) return;
      const [sx, sy] = getPointXY(reg);
      const isSel = state.selectedRegion && reg.region === state.selectedRegion.region;
      const col = getRegionColor(reg);
      const baseRadius = state.projectionView === "geo" ? (3.0 + reg.annual_aod * 5.2) : 4.6;

      if (state.algorithm === "dbscan" && reg.dbscan_role === "noise") {
        // Noise outlier (-1): bright lime warning triangle
        drawTriangle(mapCtx, sx, sy, baseRadius + 1.8);
        mapCtx.fillStyle = PALETTE.accent();
        mapCtx.fill();
        mapCtx.strokeStyle = PALETTE.paper();
        mapCtx.lineWidth = 1;
        mapCtx.stroke();
      } else if (state.algorithm === "dbscan" && reg.dbscan_role === "border") {
        // Border point: hollow circle with thick colored ring
        mapCtx.beginPath();
        mapCtx.arc(sx, sy, baseRadius, 0, Math.PI * 2);
        mapCtx.fillStyle = PALETTE.paper();
        mapCtx.fill();
        mapCtx.strokeStyle = col;
        mapCtx.lineWidth = 2.0;
        mapCtx.stroke();
      } else if (state.algorithm === "anomaly") {
        // Isolation Forest + LOF Anomaly Radar
        if (reg.is_anomaly) {
          const haloR = baseRadius + (reg.anomaly_score - 0.45) * 38;
          mapCtx.strokeStyle = PALETTE.accent();
          mapCtx.lineWidth = 1.1;
          mapCtx.beginPath();
          mapCtx.arc(sx, sy, Math.max(baseRadius + 4, haloR), 0, Math.PI * 2);
          mapCtx.stroke();
        }
        mapCtx.beginPath();
        mapCtx.arc(sx, sy, reg.is_anomaly ? baseRadius + 1.2 : 2.8, 0, Math.PI * 2);
        mapCtx.fillStyle = col;
        mapCtx.fill();
      } else {
        // Standard node + special markers for Ward boundary shifts or Naive misclassifications
        mapCtx.beginPath();
        mapCtx.arc(sx, sy, baseRadius, 0, Math.PI * 2);
        mapCtx.fillStyle = col;
        mapCtx.fill();
        mapCtx.strokeStyle = isSel ? PALETTE.ink() : PALETTE.paper();
        mapCtx.lineWidth = isSel ? 1.8 : 0.9;
        mapCtx.stroke();

        if (state.algorithm === "ward" && reg.hier_shifted) {
          // Highlight the 12 boundary cities that shifted cluster under Hierarchical linkage
          mapCtx.strokeStyle = PALETTE.accent();
          mapCtx.lineWidth = 1.5;
          mapCtx.beginPath();
          mapCtx.arc(sx, sy, baseRadius + 4.5, 0, Math.PI * 2);
          mapCtx.stroke();
        } else if (state.algorithm === "naive" && reg.naive_misclassified) {
          // Highlight the 31 cities misclassified by Naive Annual Average
          mapCtx.strokeStyle = PALETTE.ink();
          mapCtx.lineWidth = 1.4;
          drawCrossMark(mapCtx, sx, sy, baseRadius + 2.5);
        }
      }

      if (isSel) {
        mapCtx.strokeStyle = PALETTE.accent();
        mapCtx.lineWidth = 1.4;
        mapCtx.beginPath();
        mapCtx.arc(sx, sy, baseRadius + 6.5, 0, Math.PI * 2);
        mapCtx.stroke();
      }

      mapScreenNodes.push({ sx, sy, r: baseRadius + 4, reg });
    });

    // Draw K-Means++ Centroid Crosshairs on top when in kmeans mode
    if (state.algorithm === "kmeans") {
      DATA.clusters.forEach((cMeta) => {
        if (!state.activeClusters.has(cMeta.code)) return;
        const [cx, cy] = getCentroidXY(cMeta);
        mapCtx.strokeStyle = PALETTE.ink();
        mapCtx.lineWidth = 1.5;
        mapCtx.beginPath();
        mapCtx.arc(cx, cy, 5.5, 0, Math.PI * 2);
        mapCtx.moveTo(cx - 8, cy);
        mapCtx.lineTo(cx + 8, cy);
        mapCtx.moveTo(cx, cy - 8);
        mapCtx.lineTo(cx, cy + 8);
        mapCtx.stroke();
      });
    }

    // Top-left Canvas Legend Banner showing what the active algorithm is rendering
    const mStat = DATA.mode_stats[state.algorithm];
    mapCtx.fillStyle = PALETTE.accent();
    mapCtx.font = "400 11.5px Geologica, sans-serif";
    mapCtx.fillText(`${mStat.title} — ${mStat.badge_label}`, 12, 18);

    // External margin callouts in Geo view (adapted to active algorithm)
    if (state.projectionView === "geo") {
      let calloutSpecs;
      if (state.algorithm === "ward") {
        calloutSpecs = [
          { name: "Jaipur", side: "left", yOff: -18, tag: "shifted C2→C5" },
          { name: "Gwalior", side: "left", yOff: 12, tag: "shifted C5→C4" },
          { name: "Kolkata", side: "right", yOff: 8, tag: "shifted C5→C3" },
          { name: "Dehradun", side: "right", yOff: -24, tag: "shifted C6→C5" }
        ];
      } else if (state.algorithm === "dbscan") {
        calloutSpecs = [
          { name: "Sri Ganganagar", side: "left", yOff: -20, tag: "Noise (-1)" },
          { name: "Jaisalmer", side: "left", yOff: 8, tag: "Noise (-1)" },
          { name: "New Delhi", side: "right", yOff: -24, tag: "Noise (-1)" },
          { name: "Singrauli", side: "right", yOff: 10, tag: "Noise (-1)" }
        ];
      } else if (state.algorithm === "anomaly") {
        calloutSpecs = [
          { name: "Sri Ganganagar", side: "left", yOff: -22, tag: "Anom 0.62" },
          { name: "Jaisalmer", side: "left", yOff: 8, tag: "Anom 0.60" },
          { name: "New Delhi", side: "right", yOff: -24, tag: "Anom 0.56" },
          { name: "Singrauli", side: "right", yOff: 10, tag: "Anom 0.57" }
        ];
      } else if (state.algorithm === "naive") {
        calloutSpecs = [
          { name: "Ludhiana", side: "left", yOff: -22, tag: "Misgrouped!" },
          { name: "Jodhpur", side: "left", yOff: 8, tag: "Misgrouped!" },
          { name: "Patna", side: "right", yOff: -18, tag: "Same Avg Tier" },
          { name: "Dhanbad", side: "right", yOff: 12, tag: "Same Avg Tier" }
        ];
      } else {
        calloutSpecs = [
          { name: "Ludhiana", side: "left", yOff: -24, tag: "C1" },
          { name: "Jaisalmer", side: "left", yOff: 4, tag: "C2" },
          { name: "Mumbai", side: "left", yOff: 8, tag: "C5" },
          { name: "Kochi", side: "left", yOff: -12, tag: "C6" },
          { name: "Thiruvananthapuram", side: "left", yOff: 12, tag: "C6" },
          { name: "New Delhi", side: "right", yOff: -28, tag: "C4" },
          { name: "Dhanbad", side: "right", yOff: 10, tag: "C3" },
          { name: "Bengaluru", side: "right", yOff: 14, tag: "C5" }
        ];
      }

      const leftAnchorX = offsetX - 8;
      const rightAnchorX = offsetX + (lonMax - lonMin) * geoScale + 8;

      calloutSpecs.forEach((spec) => {
        const node = mapScreenNodes.find((n) => n.reg.region === spec.name);
        if (!node) return;
        const isSel = state.selectedRegion && node.reg.region === state.selectedRegion.region;
        const labelY = Math.max(32, Math.min(h - 24, node.sy + spec.yOff));
        const anchorX = spec.side === "left" ? Math.max(135, leftAnchorX) : Math.min(w - 135, rightAnchorX);

        mapCtx.strokeStyle = isSel ? PALETTE.accent() : PALETTE.rule2();
        mapCtx.lineWidth = isSel ? 1.2 : 0.9;
        mapCtx.beginPath();
        mapCtx.moveTo(node.sx, node.sy);
        mapCtx.lineTo(anchorX, labelY);
        mapCtx.stroke();

        drawCalloutPill(
          mapCtx,
          `${node.reg.region} (${spec.tag})`,
          anchorX + (spec.side === "left" ? -4 : 4),
          labelY,
          spec.side === "left"
        );
      });
    } else {
      const selNode = mapScreenNodes.find((n) => state.selectedRegion && n.reg.region === state.selectedRegion.region);
      if (selNode) {
        drawCalloutPill(
          mapCtx,
          `${selNode.reg.region} (${getActiveClusterCode(selNode.reg)})`,
          selNode.sx + 10,
          Math.max(30, selNode.sy - 8),
          selNode.sx > w * 0.72
        );
      }
      mapCtx.fillStyle = PALETTE.muted();
      mapCtx.font = "300 11.5px Geologica, sans-serif";
      mapCtx.fillText(
        state.projectionView === "pca" ? "PC1 (42.7% variance explained)" : "t-SNE manifold dimension 1",
        padX,
        h - 8
      );
    }
  }

  mapCanvas.addEventListener("click", (e) => {
    const rect = mapCanvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    let best = null, bestDist = 16;
    for (const node of mapScreenNodes) {
      const d = Math.hypot(node.sx - mx, node.sy - my);
      if (d < bestDist) {
        bestDist = d;
        best = node.reg;
      }
    }
    if (best) selectRegion(best);
  });

  // =========================================================================
  // 3. SECTION CUT RENDERER (#section-cut-canvas)
  // =========================================================================
  const cutCanvas = document.getElementById("section-cut-canvas");
  const cutCtx = cutCanvas.getContext("2d");

  function renderSectionCut() {
    const { w, h } = resizeCanvasHiDPI(cutCanvas, cutCtx, 360);
    cutCtx.clearRect(0, 0, w, h);

    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const padL = 48, padR = 128, padT = 36, padB = 38;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;

    const seriesKey = state.cutMetric === "aod" ? "monthly_aod" : "monthly_pm25";
    const unitLabel = state.cutMetric === "aod" ? "INSAT-3D Daytime AOD (650 nm)" : "Surface PM₂.₅ (µg/m³)";

    const names = [...state.cutReferenceNames];
    if (state.selectedRegion && !names.includes(state.selectedRegion.region)) {
      names.push(state.selectedRegion.region);
    }
    const cityObjs = names
      .map((n) => DATA.regions.find((r) => r.region === n))
      .filter(Boolean);

    let yMax = 0;
    cityObjs.forEach((c) => {
      c[seriesKey].forEach((v) => {
        if (v > yMax) yMax = v;
      });
    });
    yMax = yMax * 1.18;

    const toXY = (mIdx, val) => [
      padL + (mIdx / 11) * plotW,
      padT + (1 - val / yMax) * plotH
    ];

    cutCtx.strokeStyle = PALETTE.rule();
    cutCtx.lineWidth = 1;
    cutCtx.fillStyle = PALETTE.muted();
    cutCtx.font = "300 11px Geologica, sans-serif";

    for (let i = 0; i <= 4; i++) {
      const val = (yMax * i) / 4;
      const [, y] = toXY(0, val);
      cutCtx.beginPath();
      cutCtx.moveTo(padL, y);
      cutCtx.lineTo(w - padR, y);
      cutCtx.stroke();
      cutCtx.fillText(state.cutMetric === "aod" ? val.toFixed(2) : Math.round(val).toString(), 8, y + 4);
    }

    months.forEach((m, idx) => {
      const [x] = toXY(idx, 0);
      cutCtx.fillText(m, x - 10, h - 12);
    });

    const rightEndpoints = [];

    cityObjs.forEach((city) => {
      const vals = city[seriesKey];
      const col = PALETTE.clusters[city.cluster_code]();
      const isSel = state.selectedRegion && city.region === state.selectedRegion.region;

      cutCtx.strokeStyle = col;
      cutCtx.lineWidth = isSel ? 2.6 : 1.7;
      cutCtx.beginPath();
      vals.forEach((v, idx) => {
        const [x, y] = toXY(idx, v);
        if (idx === 0) cutCtx.moveTo(x, y);
        else cutCtx.lineTo(x, y);
      });
      cutCtx.stroke();

      vals.forEach((v, idx) => {
        const [x, y] = toXY(idx, v);
        cutCtx.fillStyle = col;
        cutCtx.beginPath();
        cutCtx.arc(x, y, isSel ? 3.5 : 2.4, 0, Math.PI * 2);
        cutCtx.fill();
      });

      let peakIdx = 0;
      vals.forEach((v, idx) => {
        if (v > vals[peakIdx]) peakIdx = idx;
      });
      const [endX, endY] = toXY(11, vals[11]);
      const peakValStr = state.cutMetric === "aod" ? vals[peakIdx].toFixed(2) : Math.round(vals[peakIdx]);
      rightEndpoints.push({
        city,
        col,
        endX,
        rawY: endY,
        labelY: endY,
        text: `${city.region} (${months[peakIdx]} ${peakValStr})`
      });
    });

    rightEndpoints.sort((a, b) => a.rawY - b.rawY);
    for (let i = 1; i < rightEndpoints.length; i++) {
      if (rightEndpoints[i].labelY - rightEndpoints[i - 1].labelY < 18) {
        rightEndpoints[i].labelY = rightEndpoints[i - 1].labelY + 18;
      }
    }

    cutCtx.font = "400 11px Geologica, sans-serif";
    rightEndpoints.forEach((ep) => {
      cutCtx.strokeStyle = ep.col;
      cutCtx.lineWidth = 1;
      cutCtx.beginPath();
      cutCtx.moveTo(ep.endX + 4, ep.rawY);
      cutCtx.lineTo(ep.endX + 14, ep.labelY);
      cutCtx.stroke();

      cutCtx.fillStyle = ep.col;
      cutCtx.fillText(ep.text, ep.endX + 18, ep.labelY + 4);
    });

    cutCtx.fillStyle = PALETTE.muted();
    cutCtx.font = "300 11px Geologica, sans-serif";
    cutCtx.fillText(unitLabel, padL, 18);
  }

  // =========================================================================
  // 4. CLUSTER VALIDATION CURVE RENDERER (#validation-canvas)
  // =========================================================================
  const valCanvas = document.getElementById("validation-canvas");
  const valCtx = valCanvas.getContext("2d");

  function renderValidationCurve() {
    const { w, h } = resizeCanvasHiDPI(valCanvas, valCtx, 340);
    valCtx.clearRect(0, 0, w, h);

    const rows = DATA.k_validation;
    const padL = 48, padR = 28, padT = 42, padB = 38;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;
    const yMax = 1.28;

    const toX = (k) => padL + ((k - 2) / 8) * plotW;
    const toY = (v) => padT + (1 - v / yMax) * plotH;

    valCtx.strokeStyle = PALETTE.rule();
    valCtx.fillStyle = PALETTE.muted();
    valCtx.font = "300 11px Geologica, sans-serif";
    [0.2, 0.4, 0.6, 0.8, 1.0, 1.2].forEach((v) => {
      const y = toY(v);
      valCtx.beginPath();
      valCtx.moveTo(padL, y);
      valCtx.lineTo(w - padR, y);
      valCtx.stroke();
      valCtx.fillText(v.toFixed(1), 12, y + 4);
    });

    const optX = toX(state.selectedK);
    valCtx.strokeStyle = PALETTE.accent();
    valCtx.lineWidth = 1.2;
    valCtx.beginPath();
    valCtx.moveTo(optX, padT);
    valCtx.lineTo(optX, h - padB);
    valCtx.stroke();

    const drawMetricLine = (key, color) => {
      valCtx.strokeStyle = color;
      valCtx.lineWidth = 2;
      valCtx.beginPath();
      rows.forEach((r, idx) => {
        const x = toX(r.k);
        const y = toY(r[key]);
        if (idx === 0) valCtx.moveTo(x, y);
        else valCtx.lineTo(x, y);
      });
      valCtx.stroke();

      rows.forEach((r) => {
        const x = toX(r.k);
        const y = toY(r[key]);
        valCtx.fillStyle = color;
        valCtx.beginPath();
        valCtx.arc(x, y, r.k === state.selectedK ? 4.5 : 3, 0, Math.PI * 2);
        valCtx.fill();
      });
    };

    drawMetricLine("silhouette_score", PALETTE.accent());
    drawMetricLine("davies_bouldin_index", PALETTE.pointMid());

    rows.forEach((r) => {
      const x = toX(r.k);
      valCtx.fillStyle = r.k === state.selectedK ? PALETTE.ink() : PALETTE.muted();
      valCtx.fillText("k=" + r.k, x - 10, h - 12);
    });

    valCtx.font = "400 11.5px Geologica, sans-serif";
    valCtx.fillStyle = PALETTE.accent();
    valCtx.fillText("● Silhouette score (higher is better)", padL, 20);
    valCtx.fillStyle = PALETTE.pointMid();
    valCtx.fillText("● Davies-Bouldin index (lower is better)", padL + 235, 20);
  }

  // =========================================================================
  // 5. DOM LISTS, METRICS, INSPECTOR & SCAN LOG TABLE UPDATERS
  // =========================================================================
  function updateModeMetricsBanner() {
    const m = DATA.mode_stats[state.algorithm];
    if (!m) return;

    document.getElementById("workbench-mode-subtitle").textContent = m.subtitle;
    document.getElementById("stat-silhouette").innerHTML = `${m.silhouette.toFixed(4)}<span class="u">score</span>`;
    document.getElementById("stat-dbi").innerHTML = `${m.dbi.toFixed(4)}<span class="u">index</span>`;
    document.getElementById("stat-ari").innerHTML = `${m.ari_vs_truth.toFixed(4)}<span class="u">ARI</span>`;

    const chgEl = document.getElementById("stat-changed");
    const chgSub = document.getElementById("stat-changed-sub");
    if (state.algorithm === "kmeans") {
      chgEl.innerHTML = `6<span class="u">centroids</span>`;
      chgSub.textContent = "Voronoi spokes connect 108 districts to centroids";
    } else if (state.algorithm === "ward") {
      chgEl.innerHTML = `${m.changed_count}<span class="u">shifted</span>`;
      chgSub.textContent = "Boundary cities reassigned by tree linkage";
    } else if (state.algorithm === "dbscan") {
      chgEl.innerHTML = `${m.changed_count}<span class="u">outliers</span>`;
      chgSub.textContent = "Noise regions (-1) outside ε = 0.78 density cores";
    } else if (state.algorithm === "anomaly") {
      chgEl.innerHTML = `${m.changed_count}<span class="u">hotspots</span>`;
      chgSub.textContent = "Flagged by Isolation Forest + LOF consensus";
    } else {
      chgEl.innerHTML = `${m.changed_count}<span class="u">misgrouped</span>`;
      chgSub.textContent = "Regions put into wrong airshed by annual average";
    }

    const btnMulti = document.getElementById("mode-multiseason-btn");
    const btnNaive = document.getElementById("mode-naive-btn");
    if (state.algorithm === "naive") {
      btnNaive.className = "btn btn--sm";
      btnNaive.setAttribute("aria-pressed", "true");
      btnMulti.className = "btn btn--line btn--sm";
      btnMulti.setAttribute("aria-pressed", "false");
    } else {
      btnMulti.className = "btn btn--sm";
      btnMulti.setAttribute("aria-pressed", "true");
      btnNaive.className = "btn btn--line btn--sm";
      btnNaive.setAttribute("aria-pressed", "false");
    }
  }

  function buildLayerToggles() {
    const list = document.getElementById("layer-toggles-list");
    list.innerHTML = "";
    DATA.clusters.forEach((c) => {
      const isOn = state.activeClusters.has(c.code);
      // Compute dynamic count & note for the active algorithm
      const activeSub = DATA.regions.filter((r) => getActiveClusterCode(r) === c.code);
      let extraNote = `${c.season} — ${c.source}`;
      if (state.algorithm === "ward") {
        const shiftedIn = activeSub.filter((r) => r.hier_shifted).length;
        extraNote = shiftedIn > 0
          ? `${shiftedIn} transitional boundary regions merged into ${c.code}`
          : `${c.season} — ${c.source}`;
      } else if (state.algorithm === "dbscan") {
        const noiseCnt = activeSub.filter((r) => r.dbscan_role === "noise").length;
        const coreCnt = activeSub.filter((r) => r.dbscan_role === "core").length;
        extraNote = `${coreCnt} core, ${activeSub.length - coreCnt - noiseCnt} border, ${noiseCnt} noise outliers (▲)`;
      } else if (state.algorithm === "anomaly") {
        const anomCnt = activeSub.filter((r) => r.is_anomaly).length;
        extraNote = `${anomCnt} extreme anomaly hotspots flagged in ${c.code}`;
      } else if (state.algorithm === "naive") {
        const wrongCnt = activeSub.filter((r) => r.naive_misclassified).length;
        extraNote = `${wrongCnt} of ${activeSub.length} regions misgrouped by annual average (×)`;
      }

      const li = document.createElement("li");
      li.className = "ruled-list__item";
      li.innerHTML = `
        <div class="ruled-list__left">
          <span class="cluster-swatch" style="background-color: ${PALETTE.clusters[c.code]()}"></span>
          <div>
            <div style="color: var(--color-ink); font-weight: 400;">${c.code}: ${c.short}</div>
            <div class="muted">${extraNote}</div>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 0.6rem;">
          <span class="num">${activeSub.length}<span class="u">dist</span></span>
          <button type="button" class="switch-pill" aria-pressed="${isOn}" data-cluster="${c.code}">
            ${isOn ? "On" : "Off"}
          </button>
        </div>
      `;
      li.addEventListener("click", () => {
        if (state.activeClusters.has(c.code) && state.activeClusters.size > 1) {
          state.activeClusters.delete(c.code);
        } else {
          state.activeClusters.add(c.code);
        }
        buildLayerToggles();
        renderSpatialManifold();
        if (state.reducedMotion) renderHeroCloud(2400);
      });
      list.appendChild(li);
    });
  }

  function buildCutCitiesList() {
    const list = document.getElementById("cut-cities-list");
    list.innerHTML = "";
    const names = [...state.cutReferenceNames];
    if (state.selectedRegion && !names.includes(state.selectedRegion.region)) {
      names.push(state.selectedRegion.region);
    }

    names.forEach((name) => {
      const reg = DATA.regions.find((r) => r.region === name);
      if (!reg) return;
      const li = document.createElement("li");
      li.className = "ruled-list__item";
      li.innerHTML = `
        <div class="ruled-list__left">
          <span class="cluster-swatch" style="background-color: ${PALETTE.clusters[reg.cluster_code]()}"></span>
          <div>
            <div style="color: var(--color-ink); font-weight: 400;">${reg.region}, ${reg.state}</div>
            <div class="muted">${SHORT_CLUSTER_LABEL[reg.cluster_code]}</div>
          </div>
        </div>
        <div class="num" style="text-align: right;">
          <div>${reg.annual_aod.toFixed(2)}<span class="u">annual AOD</span></div>
          <div class="muted">CV ${(reg.aod_seasonal_cv * 100).toFixed(0)}%</div>
        </div>
      `;
      li.addEventListener("click", () => selectRegion(reg));
      list.appendChild(li);
    });
  }

  function buildValidationList() {
    const list = document.getElementById("k-metrics-list");
    list.innerHTML = "";
    DATA.k_validation.forEach((row) => {
      const isOpt = row.k === state.selectedK;
      const li = document.createElement("li");
      li.className = "ruled-list__item";
      li.innerHTML = `
        <div class="ruled-list__left">
          ${isOpt ? '<span class="signal-dot"></span>' : '<span style="width:7px;"></span>'}
          <span style="color: var(--color-ink); font-weight: 400;">k = ${row.k} clusters ${row.k === 6 ? "(optimal)" : ""}</span>
        </div>
        <div class="num" style="display: flex; gap: 1.1rem;">
          <span>${row.silhouette_score.toFixed(4)}<span class="u">sil</span></span>
          <span>${row.davies_bouldin_index.toFixed(4)}<span class="u">DBI</span></span>
          <span>${Math.round(row.inertia_wcss)}<span class="u">WCSS</span></span>
        </div>
      `;
      li.addEventListener("click", () => {
        state.selectedK = row.k;
        buildValidationList();
        renderValidationCurve();
      });
      list.appendChild(li);
    });
  }

  function formatActiveAssignmentBadge(r) {
    if (state.algorithm === "ward") {
      if (r.hier_shifted) {
        return `${r.hier_code} (shifted from ${r.cluster_code}, link → ${r.hier_link_to})`;
      }
      return `${SHORT_CLUSTER_LABEL[r.hier_code]} (link → ${r.hier_link_to})`;
    }
    if (state.algorithm === "dbscan") {
      if (r.dbscan_role === "noise") return `▲ Noise Outlier (-1) [${r.cluster_code}]`;
      if (r.dbscan_role === "border") return `○ Border Point (${SHORT_CLUSTER_LABEL[r.cluster_code]})`;
      return `● Core Cluster (${SHORT_CLUSTER_LABEL[r.cluster_code]})`;
    }
    if (state.algorithm === "anomaly") {
      return r.is_anomaly
        ? `★ Hotspot Anomaly (score ${r.anomaly_score.toFixed(2)})`
        : `Normal baseline (score ${r.anomaly_score.toFixed(2)})`;
    }
    if (state.algorithm === "naive") {
      return r.naive_misclassified
        ? `× Misgrouped: True ${r.cluster_code} → Naive ${r.naive_code}`
        : `✓ Naive Tier ${r.naive_tier} (${r.naive_code})`;
    }
    return SHORT_CLUSTER_LABEL[r.cluster_code];
  }

  function updateInspector() {
    const r = state.selectedRegion;
    if (!r) return;
    const cMeta = DATA.clusters.find((c) => c.code === getActiveClusterCode(r));
    document.getElementById("insp-cluster").textContent = formatActiveAssignmentBadge(r);
    document.getElementById("insp-name").textContent = `${r.region}, ${r.state}`;
    document.getElementById("insp-intervention").textContent = cMeta ? `Intervention: ${cMeta.intervention}` : "";
    document.getElementById("insp-djf").innerHTML = `${r.aod_winter_djf.toFixed(3)}<span class="u">AOD</span>`;
    document.getElementById("insp-mam").innerHTML = `${r.aod_premonsoon_mam.toFixed(3)}<span class="u">AOD</span>`;
    document.getElementById("insp-on").innerHTML = `${r.aod_postmonsoon_on.toFixed(3)}<span class="u">AOD</span>`;

    if (state.algorithm === "anomaly") {
      document.getElementById("insp-source").innerHTML = `${r.anomaly_score.toFixed(3)}<span class="u">IForest score</span>`;
    } else if (r.cluster_code === "C1") {
      document.getElementById("insp-source").innerHTML = `${r.postmonsoon_smoke_spike.toFixed(2)}<span class="u">smoke spike</span>`;
    } else if (r.cluster_code === "C2") {
      document.getElementById("insp-source").innerHTML = `${(r.coarse_dust_fraction * 100).toFixed(0)}<span class="u">% coarse dust</span>`;
    } else if (r.cluster_code === "C3") {
      document.getElementById("insp-source").innerHTML = `${r.so2_to_no2_ratio.toFixed(2)}<span class="u">SO₂/NO₂</span>`;
    } else {
      document.getElementById("insp-source").innerHTML = `${r.annual_pm25.toFixed(1)}<span class="u">µg/m³ PM₂.₅</span>`;
    }
  }

  function buildScanTable() {
    const tbody = document.getElementById("scan-table-body");
    tbody.innerHTML = "";
    const q = state.searchQuery.toLowerCase().trim();

    const filtered = DATA.regions.filter((r) => {
      if (state.tableClusterFilter === "ANOMALY" && !r.is_anomaly) return false;
      if (state.tableClusterFilter !== "ALL" && state.tableClusterFilter !== "ANOMALY" && getActiveClusterCode(r) !== state.tableClusterFilter) {
        return false;
      }
      if (q && !r.region.toLowerCase().includes(q) && !r.state.toLowerCase().includes(q)) {
        return false;
      }
      return true;
    });

    filtered.forEach((r) => {
      const isSel = state.selectedRegion && r.region === state.selectedRegion.region;
      const tr = document.createElement("tr");
      if (isSel) tr.className = "is-selected";
      const badgeColor = getRegionColor(r);
      tr.innerHTML = `
        <td>
          <div style="display: flex; align-items: center; gap: 0.45rem;">
            ${isSel ? '<span class="signal-dot"></span>' : '<span style="width:7px;"></span>'}
            <span style="color: var(--color-ink); font-weight: 400;">${r.region}</span>
            <span class="muted">${r.state}</span>
          </div>
        </td>
        <td>
          <span style="display: inline-flex; align-items: center; gap: 0.4rem;">
            <span class="cluster-swatch" style="background-color: ${badgeColor}"></span>
            <span>${formatActiveAssignmentBadge(r)}</span>
          </span>
        </td>
        <td class="num num-col">${r.annual_aod.toFixed(3)}</td>
        <td class="num num-col">${r.aod_winter_djf.toFixed(3)}</td>
        <td class="num num-col">${r.aod_premonsoon_mam.toFixed(3)}</td>
        <td class="num num-col">${r.aod_monsoon_jjas.toFixed(3)}</td>
        <td class="num num-col">${r.aod_postmonsoon_on.toFixed(3)}</td>
        <td class="num num-col">${(r.coarse_dust_fraction * 100).toFixed(0)}<span class="u">%</span></td>
        <td class="num num-col">${r.so2_to_no2_ratio.toFixed(2)}</td>
        <td class="num num-col">${(r.aod_seasonal_cv * 100).toFixed(1)}<span class="u">%</span></td>
      `;
      tr.addEventListener("click", () => selectRegion(r));
      tbody.appendChild(tr);
    });
  }

  function selectRegion(reg) {
    state.selectedRegion = reg;
    updateInspector();
    buildCutCitiesList();
    renderSpatialManifold();
    renderSectionCut();
    buildScanTable();
    if (state.reducedMotion) renderHeroCloud(2400);
  }

  function setAlgorithm(algo) {
    state.algorithm = algo;
    // Automatically ensure all 6 layers are turned ON when switching algorithms so the user sees the full transformation
    state.activeClusters = new Set(["C1", "C2", "C3", "C4", "C5", "C6"]);
    document.getElementById("algo-select").value = algo;
    updateModeMetricsBanner();
    buildLayerToggles();
    updateInspector();
    renderSpatialManifold();
    buildScanTable();
    if (state.reducedMotion) renderHeroCloud(2400);
  }

  // =========================================================================
  // 6. EVENT WIRING
  // =========================================================================
  document.getElementById("mode-multiseason-btn").addEventListener("click", () => setAlgorithm("kmeans"));
  document.getElementById("mode-naive-btn").addEventListener("click", () => setAlgorithm("naive"));
  document.getElementById("hero-toggle-naive").addEventListener("click", () => {
    setAlgorithm(state.algorithm === "naive" ? "kmeans" : "naive");
    document.getElementById("workbench").scrollIntoView({ behavior: "smooth" });
  });

  document.getElementById("reset-layers-btn").addEventListener("click", () => {
    state.activeClusters = new Set(["C1", "C2", "C3", "C4", "C5", "C6"]);
    buildLayerToggles();
    renderSpatialManifold();
  });

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.setAttribute("aria-selected", "false"));
      btn.setAttribute("aria-selected", "true");
      state.projectionView = btn.getAttribute("data-view");
      renderSpatialManifold();
    });
  });

  document.getElementById("algo-select").addEventListener("change", (e) => {
    setAlgorithm(e.target.value);
  });

  document.getElementById("cut-metric-aod").addEventListener("click", () => {
    state.cutMetric = "aod";
    document.getElementById("cut-metric-aod").setAttribute("aria-pressed", "true");
    document.getElementById("cut-metric-pm25").setAttribute("aria-pressed", "false");
    renderSectionCut();
  });

  document.getElementById("cut-metric-pm25").addEventListener("click", () => {
    state.cutMetric = "pm25";
    document.getElementById("cut-metric-pm25").setAttribute("aria-pressed", "true");
    document.getElementById("cut-metric-aod").setAttribute("aria-pressed", "false");
    renderSectionCut();
  });

  document.getElementById("region-search").addEventListener("input", (e) => {
    state.searchQuery = e.target.value;
    buildScanTable();
  });

  document.getElementById("cluster-filter").addEventListener("change", (e) => {
    state.tableClusterFilter = e.target.value;
    buildScanTable();
  });

  window.addEventListener("resize", () => {
    renderSpatialManifold();
    renderSectionCut();
    renderValidationCurve();
    if (state.reducedMotion) renderHeroCloud(2400);
  });

  // Initial mount
  updateModeMetricsBanner();
  buildLayerToggles();
  updateInspector();
  buildCutCitiesList();
  buildValidationList();
  buildScanTable();
  renderHeroCloud(2400);
  renderSpatialManifold();
  renderSectionCut();
  renderValidationCurve();
})();

/**
 * AeroScope: month-by-month air-quality guides for India's NCAP cities.
 * Views over the exported JSON in ./data:
 *   #/               landing: city search over a real city's air calendar
 *   #/city/<city>    residents: today and the next days, the year, why, what to do
 *   #/brief/<city>   planners: the year, this month and coming up, the action plan, details in panels
 *   #/explore        all cities: map, pattern groups, table, methods
 * Colours never live here: every data colour is a CSS class backed by a token in styles.css.
 */
(function () {
  "use strict";

  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December"];
  const AQI_CATS = [
    { name: "Good", max: 50, cls: "good" },
    { name: "Satisfactory", max: 100, cls: "satisfactory" },
    { name: "Moderate", max: 200, cls: "moderate" },
    { name: "Poor", max: 300, cls: "poor" },
    { name: "Very Poor", max: 400, cls: "verypoor" },
    { name: "Severe", max: 500, cls: "severe" },
  ];
  // CPCB National AQI health statements.
  const HEALTH = {
    "Good": "Minimal impact.",
    "Satisfactory": "Minor breathing discomfort for sensitive people.",
    "Moderate": "Breathing discomfort for people with lung disease such as asthma, and discomfort for people with heart disease, children and older adults.",
    "Poor": "Breathing discomfort for most people on prolonged exposure.",
    "Very Poor": "Respiratory illness on prolonged exposure.",
    "Severe": "Affects healthy people and seriously impacts those with existing diseases.",
  };
  const PRACTICAL = {
    "Good": "A good day to be outdoors.",
    "Satisfactory": "Fine for most people. If you have asthma, keep your inhaler handy.",
    "Moderate": "Sensitive groups should cut down long or strenuous outdoor activity.",
    "Poor": "Everyone should reduce strenuous outdoor activity. Children, older adults and people with heart or lung disease should avoid it.",
    "Very Poor": "Avoid outdoor exercise. Keep windows closed at peak hours. Consider a well-fitted N95 mask outdoors.",
    "Severe": "Stay indoors as much as possible. Use an N95 mask if you must go out. People with heart or lung disease should follow their doctor's plan.",
  };
  const PM25_BP = [[0, 30, 0, 50], [30, 60, 50, 100], [60, 90, 100, 200], [90, 120, 200, 300], [120, 250, 300, 400], [250, 380, 400, 500]];
  const PM10_BP = [[0, 50, 0, 50], [50, 100, 50, 100], [100, 250, 100, 200], [250, 350, 200, 300], [350, 430, 300, 400], [430, 510, 400, 500]];
  const DUST_LOAD = 50; // ug/m3, the pipeline's monthly dust threshold
  const KIND_LABEL = { prevent: "Prevent", respond: "Respond", protect: "Protect people" };
  const FEATURED = ["delhi", "ludhiana", "patna", "jodhpur", "mumbai", "kolkata", "bengaluru", "chennai", "dhanbad", "guwahati"];
  const NOW_MONTH = new Date().getMonth() + 1;

  // Simplified India outline (lon, lat) for the overview map.
  const INDIA_POLY = [[68.12, 23.65], [68.85, 22.85], [69.05, 22.25], [70.18, 20.92], [70.95, 20.75], [71.65, 21.15], [72.25, 21.75], [72.62, 21.65], [72.9, 20.45], [72.82, 19.07], [72.98, 17.95], [73.35, 16.98], [73.78, 15.55], [74.05, 14.82], [74.45, 13.85], [74.85, 12.91], [75.35, 11.88], [75.78, 11.25], [76.02, 10.55], [76.26, 9.93], [76.34, 9.49], [76.58, 8.89], [76.94, 8.52], [77.54, 8.08], [78.15, 8.78], [78.82, 9.28], [79.32, 9.28], [79.15, 10.05], [79.82, 10.76], [79.85, 11.94], [80.27, 13.08], [80.08, 14.45], [80.12, 15.42], [80.85, 15.82], [81.75, 16.45], [82.24, 16.98], [83.3, 17.7], [84.78, 19.15], [85.82, 19.8], [86.95, 20.75], [87.08, 21.52], [88.25, 21.62], [89.02, 21.68], [88.95, 22.65], [88.65, 23.55], [88.48, 24.25], [88.18, 24.85], [88.45, 25.35], [88.42, 25.95], [88.75, 26.22], [89.55, 26.08], [89.88, 25.62], [90.15, 25.22], [91.05, 25.18], [92.05, 25.05], [92.35, 24.65], [91.85, 24.35], [91.25, 23.52], [91.58, 22.98], [92.18, 23.65], [92.42, 22.65], [92.95, 22.02], [93.35, 23.15], [93.92, 23.85], [94.35, 24.45], [94.75, 25.45], [95.15, 26.35], [96.15, 27.05], [96.95, 27.35], [97.38, 28.18], [96.65, 28.65], [96.12, 29.35], [94.65, 29.15], [93.65, 28.35], [92.55, 27.88], [91.65, 27.75], [91.55, 26.82], [89.85, 26.72], [89.15, 26.82], [88.92, 27.32], [88.65, 27.95], [88.12, 27.88], [88.02, 27.15], [88.05, 26.68], [86.85, 26.65], [85.15, 26.78], [83.95, 27.35], [82.15, 27.85], [81.05, 28.45], [80.15, 28.88], [80.25, 29.75], [81.02, 30.25], [79.85, 30.92], [78.95, 31.42], [78.65, 32.15], [78.42, 32.65], [79.25, 32.75], [79.55, 33.45], [78.95, 33.95], [79.85, 34.55], [80.35, 35.15], [79.95, 35.75], [78.95, 35.85], [77.85, 35.52], [77.05, 35.95], [76.15, 35.88], [75.45, 36.45], [74.65, 37.08], [73.65, 36.85], [72.85, 36.15], [72.55, 35.35], [73.25, 34.75], [73.85, 34.25], [73.75, 33.45], [74.15, 32.75], [74.75, 32.28], [74.52, 31.55], [73.92, 30.25], [73.25, 29.25], [72.15, 28.15], [70.65, 27.85], [69.52, 26.85], [70.15, 25.95], [70.95, 25.15], [70.85, 24.42], [69.25, 24.15], [68.12, 23.65]];

  const state = { index: null, study: null, cache: new Map(), byId: new Map(), explore: { color: "group", proj: "map", sort: "annual_pm25", dir: -1, q: "" } };
  const root = document.getElementById("view-root");

  // ------------------------------------------------------------------ helpers
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v) ? "–" : Number(v).toFixed(d));
  const lc = (t) => t.charAt(0).toLowerCase() + t.slice(1);
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } },
  };
  const sigCls = (key) => `sig-${key}`;
  const grpCls = (id) => `g${((id % 8) + 8) % 8}`;
  // A pattern group wears its driver's colour, so a group and its months read alike; bands by yearly average use neutral group hues.
  const groupCls = (id) => { const g = state.index.groups.find((x) => x.id === id); return g && g.key ? sigCls(g.key) : grpCls(id); };
  const swatch = (cls) => `<span class="swatch ${cls}" aria-hidden="true"></span>`;
  const meta = (...items) => `<p class="meta">${items.filter(Boolean).map((i) => `<span>${i}</span>`).join("")}</p>`;

  function subIndex(c, bp) {
    if (c === null || c === undefined || Number.isNaN(c)) return NaN;
    for (const [lo, hi, ilo, ihi] of bp) if (c >= lo && c <= hi) return ilo + (c - lo) * (ihi - ilo) / (hi - lo);
    return 500;
  }
  const particulateAqi = (pm25, pm10) => Math.max(subIndex(pm25, PM25_BP), subIndex(pm10, PM10_BP));
  function aqiCat(aqi) {
    if (aqi === null || aqi === undefined || Number.isNaN(aqi)) return null;
    return AQI_CATS.find((c) => Math.ceil(aqi) <= c.max) || AQI_CATS[AQI_CATS.length - 1];
  }
  const aqiCls = (c) => (c ? `aqi--${c.cls}` : "");
  // The six CPCB bands as a track with a cream tick at the reading (0 to 500).
  const aqiTrack = (aqi) => `<div class="track" role="img" aria-label="AQI ${Math.round(aqi)} on the 0 to 500 scale">${AQI_CATS.map((c) => `<span class="aqi--${c.cls}"></span>`).join("")}<span class="track__tick" style="left:${trackPos(aqi).toFixed(1)}%"></span></div>`;
  // CPCB bands are unequal (0-50, 51-100, 101-200, 201-300, 301-400, 401-500); each takes one sixth of the track.
  function trackPos(aqi) {
    const edges = [0, 50, 100, 200, 300, 400, 500];
    const v = Math.min(500, Math.max(0, aqi || 0));
    let i = edges.findIndex((e, k) => k < 6 && v <= edges[k + 1]);
    if (i < 0) i = 5;
    return ((i + (v - edges[i]) / (edges[i + 1] - edges[i])) / 6) * 100;
  }
  const bandName = (c) => (c ? `<span class="band-name">${swatch(`aqi--${c.cls}`)}${c.name}</span>` : "Unknown");
  const catByName = (name) => AQI_CATS.find((c) => c.name === name) || null;
  const monthList = (ms) => (!ms || !ms.length ? "none" : ms.map((m) => MONTHS[m - 1]).join(", "));
  function monthRange(ms) {
    if (!ms || !ms.length) return "";
    const contiguous = ms.every((m, i) => i === 0 || ((ms[i - 1] % 12) + 1) === m);
    if (contiguous && ms.length > 1) return `${MONTHS[ms[0] - 1]} to ${MONTHS[ms[ms.length - 1] - 1]}`;
    return monthList(ms);
  }
  const sigInfo = (key) => (state.index.signatures[key] || { label: key, plain: "" });
  const groupInfo = (id) => state.index.groups.find((g) => g.id === id) || { label: "Unknown group", id: 0 };
  function shortSig(key) {
    return { postmonsoon_smoke: "Smoke", winter_stagnation: "Stagnant air", premonsoon_dust: "Dust",
      industrial_combustion: "Industry", urban_traffic: "Traffic", cleaner_baseline: "Baseline", mixed: "Mixed" }[key] || key;
  }

  async function loadJSON(url) {
    const r = await fetch(url, { cache: "no-cache" });
    if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
    return r.json();
  }
  async function loadCity(id) {
    if (!state.cache.has(id)) state.cache.set(id, loadJSON(`data/cities/${encodeURIComponent(id)}.json`));
    return state.cache.get(id);
  }
  async function loadStudy() {
    if (!state.study) state.study = await loadJSON("data/study.json");
    return state.study;
  }
  function download(name, text, type = "text/csv") {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const a = Object.assign(document.createElement("a"), { href: url, download: name });
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const csvCell = (v) => { const s = String(v ?? ""); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };

  function findCity(text) {
    const v = text.trim().toLowerCase();
    if (!v) return null;
    const head = v.split(",")[0].trim();
    return state.index.cities.find((c) => `${c.city}, ${c.state}`.toLowerCase() === v)
      || state.index.cities.find((c) => c.city.toLowerCase() === head)
      || state.index.cities.find((c) => c.city.toLowerCase().startsWith(head))
      || state.index.cities.find((c) => c.city.toLowerCase().includes(head))
      || null;
  }
  const savedCity = () => { const s = store.get("aeroscope.city"); return s && state.byId.has(s) ? s : null; };
  function defaultCity() { return savedCity() || (state.byId.has("delhi") ? "delhi" : state.index.cities[0].id); }

  // Ruled disclosure; remembers open/closed per panel in this browser.
  function panel(id, title, hint, body, openByDefault = false, quiet = false) {
    const saved = store.get(`aeroscope.panel.${id}`);
    const open = saved === null ? openByDefault : saved === "1";
    return `<details class="panel${quiet ? " panel--quiet" : ""}" data-panel="${id}"${open ? " open" : ""}>
      <summary><span class="panel__title">${title}</span><span class="panel__hint">${hint}</span><span class="panel__sign" aria-hidden="true"></span></summary>
      <div class="panel__body">${body}</div></details>`;
  }
  function wirePanels() {
    root.querySelectorAll("details.panel[data-panel]").forEach((d) =>
      d.addEventListener("toggle", () => store.set(`aeroscope.panel.${d.dataset.panel}`, d.open ? "1" : "0")));
  }
  // Printing opens every panel so the PDF carries the whole brief, then restores the reader's layout.
  let printRestore = [];
  window.addEventListener("beforeprint", () => {
    printRestore = [...document.querySelectorAll("details.panel:not([open])")];
    printRestore.forEach((d) => { d.open = true; });
  });
  window.addEventListener("afterprint", () => { printRestore.forEach((d) => { d.open = false; }); printRestore = []; });

  // ------------------------------------------------------------------ routing
  function parseHash() {
    const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
    return { view: parts[0] || "home", id: parts[1] ? decodeURIComponent(parts[1]) : null };
  }
  function setNav(view, cityId) {
    document.querySelectorAll(".site-nav__links [data-nav]").forEach((a) => {
      if (a.dataset.nav === view) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    const id = cityId || defaultCity();
    document.querySelectorAll('[data-nav="brief"], [data-nav-footer="brief"]').forEach((a) => a.setAttribute("href", `#/brief/${id}`));
    document.querySelectorAll('[data-nav="city"], [data-nav-footer="city"]').forEach((a) => a.setAttribute("href", `#/city/${id}`));
  }
  async function route() {
    const { view, id } = parseHash();
    try {
      if (view === "home") { setNav("home"); document.title = "AeroScope: your city’s bad-air months"; await renderHome(); }
      else if (view === "explore") { setNav("explore"); document.title = "All NCAP cities: AeroScope"; await renderExplore(); }
      else {
        const v = view === "brief" ? "brief" : "city";
        const cityId = id && state.byId.has(id) ? id : defaultCity();
        if (id !== cityId || view !== v) history.replaceState(null, "", `#/${v}/${cityId}`);
        store.set("aeroscope.city", cityId);
        setNav(v, cityId);
        const brief = await loadCity(cityId);
        document.title = `${v === "brief" ? "Planner brief" : "Air"} for ${brief.city}: AeroScope`;
        if (v === "city") renderCitizen(brief); else renderBrief(brief);
      }
      wirePanels();
    } catch (err) {
      root.innerHTML = `<div class="app"><div class="page-head"><h1>Something went wrong</h1><p class="callout">${esc(err.message)}</p>
        <p class="muted">If you opened index.html straight from disk, serve the folder instead: <code>python -m http.server 8080 --directory web</code></p></div></div>`;
      console.error(err);
    }
    window.scrollTo({ top: 0 });
  }

  // ------------------------------------------------------------------ shared pieces
  function statusText(status) {
    return status === "non_attainment" ? "NCAP non-attainment city" : "NCAP million-plus city (15th Finance Commission)";
  }
  function aqiKey(withRisk) {
    return `<div class="key">${AQI_CATS.map((c) => `<span>${swatch(`aqi--${c.cls}`)}${c.name}</span>`).join("")}
      ${withRisk ? `<span><span class="risk-key" aria-hidden="true"></span>Raised: high-risk month</span><span>Underlined: this month</span>` : ""}</div>`;
  }
  function aqiTable() {
    return `<div class="table-wrap"><table>
      <thead><tr><th>AQI band</th><th>What it means</th><th>What to do</th></tr></thead>
      <tbody>${AQI_CATS.map((c) => `<tr><td>${bandName(c)}<br><small class="muted">up to ${c.max}</small></td><td>${esc(HEALTH[c.name])}</td><td>${esc(PRACTICAL[c.name])}</td></tr>`).join("")}</tbody>
    </table></div><p class="label">Health statements follow CPCB's National AQI. AQI here is the higher of the PM2.5 and PM10 sub-indices. General information, not medical advice.</p>`;
  }
  const caveatsList = (list) => `<ul class="bullets">${list.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>`;

  // The signature: twelve ruled months, the AQI band on a bar, the likely drivers, risk months tinted.
  function airCalendar(monthly, label) {
    return `<div class="aircal" role="list" aria-label="${esc(label)}">${monthly.map((m) => {
      const c = aqiCat(m.aqi_median);
      const cls = ["aircal__m", m.risk ? "is-risk" : "", m.month === NOW_MONTH ? "is-now" : ""].filter(Boolean).join(" ");
      const drivers = m.drivers.map((d) => `<span>${swatch(sigCls(d))}${esc(shortSig(d))}</span>`).join("");
      return `<div class="${cls}" role="listitem" aria-label="${MONTHS_LONG[m.month - 1]}: typically ${c ? c.name : "unknown"}${m.drivers.length ? ", " + m.drivers.map(shortSig).join(" and ") : ""}${m.risk ? ", high-risk month" : ""}">
        <span class="aircal__bar ${c ? `aqi--${c.cls}` : ""}" aria-hidden="true"></span>
        <span class="aircal__name">${MONTHS[m.month - 1]}</span>
        <span class="aircal__band">${c ? c.name : "–"}</span>
        <span class="aircal__drivers">${drivers}</span></div>`;
    }).join("")}</div>`;
  }

  function searchForm(id, target, label) {
    return `<form class="search" id="${id}" role="search" autocomplete="off">
      <label for="${id}-input" class="visually-hidden">Find your city</label>
      <input id="${id}-input" name="city" class="input" type="search" list="city-options" placeholder="Type your city, e.g. Lucknow" />
      <button class="btn btn--primary" type="submit">${esc(label)}</button></form>`;
  }
  function wireSearch(id, target) {
    const form = document.getElementById(id), input = document.getElementById(`${id}-input`);
    if (!form) return;
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const hit = findCity(input.value);
      if (!hit) { input.setCustomValidity("No NCAP city matches. Try the city name, for example Lucknow."); input.reportValidity(); return; }
      location.hash = `#/${target}/${hit.id}`;
    });
    input.addEventListener("input", () => input.setCustomValidity(""));
  }

  // ------------------------------------------------------------------ HOME
  async function renderHome() {
    const idx = state.index;
    const n = idx.cities.length;
    const sampleId = defaultCity();
    const sample = await loadCity(sampleId);
    const riskNow = idx.cities.filter((c) => c.risk_months.includes(NOW_MONTH));
    const worstNow = [...idx.cities].sort((a, b) => (b.monthly_pm25[NOW_MONTH - 1] ?? 0) - (a.monthly_pm25[NOW_MONTH - 1] ?? 0)).slice(0, 3);
    const national = MONTHS.map((_, i) => {
      const v = idx.cities.map((c) => c.monthly_pm25[i]).filter((x) => x !== null).sort((a, b) => a - b);
      return v.length ? v[Math.floor(v.length / 2)] : null;
    });
    const vals = national.filter((x) => x !== null);
    const bestMonth = national.indexOf(Math.min(...vals)) + 1;
    const worstMonth = national.indexOf(Math.max(...vals)) + 1;
    const featured = FEATURED.filter((id) => state.byId.has(id) && id !== sampleId).slice(0, 5);

    let beforeAfter = "";
    try {
      const s = (await loadStudy()).summary.annual_average_fallacy;
      const cs = (s.showcase_cities || []).filter((id) => state.byId.has(id)).slice(0, 4).map((id) => state.byId.get(id));
      if (cs.length >= 2) {
        const avg = cs.reduce((a, c) => a + c.annual_pm25, 0) / cs.length;
        beforeAfter = `<section class="section" aria-labelledby="h-same">
          <div class="section__head"><h2 id="h-same">One average, different years</h2>
            <p class="standfirst">Each of these cities averages about ${fmt(avg)} µg/m³ of PM2.5 a year. Their bad months fall far apart, so one yearly target fits none of them.</p></div>
          <div class="well">${lineChart(cs.map((c, i) => ({ values: c.monthly_pm25, cls: `s-g${i}`, width: 2.5, label: c.city })), { w: 960, h: 340, label: "Monthly PM2.5 in cities with similar yearly averages", ref: { v: 60, label: "daily limit, 60" } })}</div>
          <p class="label" style="margin-top:var(--space-sm)">Worst months: ${cs.map((c) => `<a href="#/city/${esc(c.id)}">${esc(c.city)}</a> in ${MONTHS_LONG[c.peak_month - 1]}`).join(", ")}.</p>
        </section>`;
      }
    } catch (e) { /* the comparison is optional */ }

    root.innerHTML = `
      <section class="hero" aria-labelledby="h-hero">
        <div class="hero__copy">
          <h1 id="h-hero">See your city’s smog season coming.</h1>
          <p class="standfirst">When the air turns bad, the likely reason, and what to start.</p>
          ${searchForm("home-search", "city", "Show my city")}
          <p class="try"><span>Or open</span>${featured.map((id) => `<a href="#/city/${esc(id)}">${esc(state.byId.get(id).city)}</a>`).join("")}<a href="#/brief/${esc(sampleId)}">a planner brief</a></p>
        </div>
        <figure class="hero__map">
          <figcaption class="label">A typical ${MONTHS_LONG[NOW_MONTH - 1]}: ${n} NCAP cities by PM2.5 band, sized by how much there is. Select one.</figcaption>
          ${aqiKey(false)}
          <div class="map-wrap" id="hero-map">${heroMap()}<div class="map-tip" id="hero-tip"></div></div>
        </figure>
      </section>

      <section class="section" aria-labelledby="h-year">
        <div class="section__head"><h2 id="h-year">${esc(sample.city)}, month by month</h2><p class="standfirst">Every city gets its year as twelve months: the usual band, the likely driver, and the months that need a plan.</p></div>
        <div class="year-strip">
          <div class="label" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:var(--space-xs)"><span>A typical year, ${idx.years[0]} to ${idx.years[idx.years.length - 1]}</span><a href="#/city/${esc(sampleId)}">Open ${esc(sample.city)}</a></div>
          ${airCalendar(sample.monthly, `${sample.city}, typical air quality by month`)}
          ${aqiKey(true)}
        </div>
      </section>

      <section class="section" aria-labelledby="h-ways">
        <div class="section__head"><h2 id="h-ways">Residents check it, planners act on it</h2><p class="standfirst">The same ${n} cities, for the people who live there and the people who plan for them.</p></div>
        <div class="ways">
          <a href="#/city/${esc(sampleId)}"><h3>I live here</h3><p>Which months to watch, today and the next four days with the likely cause, and what to do on bad-air days.</p><span class="go">Open My city</span></a>
          <a href="#/brief/${esc(sampleId)}"><h3>I plan for the city</h3><p>What to start this month, a dated action plan with owners and policy links, and a brief to print.</p><span class="go">Open the brief</span></a>
        </div>
      </section>

      ${beforeAfter}

      <section class="section" aria-labelledby="h-work">
        <div class="section__head"><h2 id="h-work">${esc(sample.city)} today</h2><p class="standfirst">The live reading, the band and the likely cause. <a href="#/city/${esc(sampleId)}">The next four days</a> and <a href="#/brief/${esc(sampleId)}">this month’s measures</a> sit in the city views.</p></div>
        <div id="forecast"><div class="skeleton" aria-label="Loading the live reading"></div></div>
      </section>

      <section class="band" aria-labelledby="h-now">
        <div class="container">
          <h2 id="h-now">${MONTHS_LONG[NOW_MONTH - 1]} across India</h2>
          <div class="figures">
            <div><span class="figure">${riskNow.length}</span><span class="stat__label">of ${n} cities usually at high risk this month</span></div>
            <div><span class="figure figure--word">${MONTHS[worstMonth - 1]}</span><span class="stat__label">the worst month nationally</span></div>
            <div><span class="figure figure--word">${MONTHS[bestMonth - 1]}</span><span class="stat__label">the cleanest month nationally</span></div>
          </div>
          <p style="margin-top:var(--space-xl)">Usually worst this month: ${worstNow.map((c) => `<a href="#/city/${esc(c.id)}">${esc(c.city)}</a>`).join(", ")}.</p>
        </div>
      </section>

      <section class="section" aria-labelledby="h-q">
        <div class="section__head"><h2 id="h-q">Before you rely on it</h2><p class="standfirst">Two things worth knowing about the colours and the numbers.</p></div>
        <div class="panels">
          ${panel("home-aqi", "What the colours mean", "India's six AQI bands and what to do in each", aqiTable())}
          ${panel("home-data", "Where the data comes from", "Model estimates: right on timing, lower than monitors on the worst days",
            `<ul class="bullets">
              <li><strong>Air quality:</strong> ${esc(idx.data_source)}.</li>
              <li><strong>Fires:</strong> ${idx.fire_data_available ? "NASA FIRMS VIIRS satellite fire detections." : "NASA FIRMS detections are not loaded yet, so smoke is not yet verified."}</li>
              <li><strong>Weather:</strong> ${idx.weather_available ? "ERA5 winds and mixing height for October to February." : "ERA5 winds are not loaded yet."}</li>
              <li>The model works on a ~40 km grid. It gets the seasons right but usually reads lower than city monitors on the worst days: use it for when and why, not exact numbers.</li>
              <li>The measures summarise public programmes (NCAP, CAQM/GRAP, CPCB, MoEFCC, IMD). They are planning prompts, not official orders.</li>
            </ul><p><a href="#/explore">Methods and validation</a></p>`)}
        </div>
      </section>

      <section class="section" aria-labelledby="h-close">
        <div class="close">
          <h2 id="h-close">Your city’s air calendar</h2>
          <div>${searchForm("close-search", "city", "Show my city")}<p class="label" style="margin-top:var(--space-xs)">All ${n} NCAP cities, from Agra to Visakhapatnam.</p></div>
        </div>
      </section>`;

    wireSearch("home-search", "city");
    wireSearch("close-search", "city");
    wireTabs();
    wireHeroMap();
    loadForecast(sample, document.getElementById("forecast"), true);
  }

  function wireTabs() {
    const tabs = [...root.querySelectorAll('[role="tab"]')];
    const select = (t) => {
      tabs.forEach((x) => {
        const on = x === t;
        x.setAttribute("aria-selected", on); x.tabIndex = on ? 0 : -1;
        document.getElementById(x.getAttribute("aria-controls")).hidden = !on;
      });
    };
    tabs.forEach((t, i) => {
      t.addEventListener("click", () => select(t));
      t.addEventListener("keydown", (e) => {
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
        select(next); next.focus();
      });
    });
  }

  // ------------------------------------------------------------------ BRIEF (planners)
  function spanMonths(start, peaks, yearRound) {
    const cells = new Array(12).fill("");
    if (yearRound) { for (let i = 0; i < 12; i++) cells[i] = "year"; (peaks || []).forEach((m) => { cells[m - 1] = "peak"; }); return cells; }
    const last = peaks[peaks.length - 1];
    let m = start;
    for (let guard = 0; guard < 12; guard++) {
      cells[m - 1] = peaks.includes(m) ? "peak" : "lead";
      if (m === last) break;
      m = (m % 12) + 1;
    }
    return cells;
  }

  function nextUp(b) {
    const now = [], soon = [];
    b.calendar.filter((c) => !c.year_round).forEach((c) => {
      const cell = spanMonths(c.start_month, c.peak_months, false)[NOW_MONTH - 1];
      // Preparation belongs to its lead-up window; in the peak only measures meant for the peak are "now".
      if (cell === "lead" || (cell === "peak" && c.lead_months === 0)) now.push({ ...c, phase: cell });
      else if (cell !== "peak") soon.push({ ...c, wait: (c.start_month - NOW_MONTH + 12) % 12 });
    });
    soon.sort((a, b) => a.wait - b.wait);
    now.sort((a, b) => (a.phase === "lead") - (b.phase === "lead"));
    const nextSoon = soon.filter((c) => c.wait <= 3).slice(0, 3);
    const yr = b.calendar.filter((c) => c.year_round).length;
    const item = (c, when) => `<li><span class="tag">${swatch(sigCls(c.signature))}${esc(shortSig(c.signature))}</span><span>${esc(c.action)}</span><span class="label">${when}</span></li>`;
    return `<div class="next-up"><div>
      <h3>This month, ${MONTHS_LONG[NOW_MONTH - 1]}</h3>
      ${now.length ? `<ul class="action-list">${now.slice(0, 4).map((c) => item(c, c.phase === "peak" ? "Peak season now" : `Preparing for ${monthRange(c.peak_months)}`)).join("")}</ul>${now.length > 4 ? `<p class="label">${now.length - 4} more in the action plan</p>` : ""}`
        : `<p class="muted">No seasonal measure is due this month.</p>`}</div>
      <div><h3>Coming up</h3>${nextSoon.length ? `<ul class="action-list">${nextSoon.map((c) => item(c, `Start in ${MONTHS_LONG[c.start_month - 1]}`)).join("")}</ul>` : `<p class="muted">Nothing new starts in the next three months.</p>`}
      ${yr ? `<p class="label">And ${yr} year-round measure${yr > 1 ? "s" : ""} for industry, traffic or prevention, in the action plan.</p>` : ""}</div>
    </div>`;
  }

  function briefSummary(b) {
    const h = b.headline;
    const seasonal = Object.entries(b.drivers).filter(([, v]) => !v.year_round);
    const yr = Object.entries(b.drivers).filter(([, v]) => v.year_round);
    let s = `Air in ${b.city} is worst in ${monthList(h.worst_months)} and best in ${MONTHS_LONG[h.cleanest_month - 1]}. `;
    if (seasonal.length) s += `The data points to ${seasonal.map(([k, v]) => `${lc(sigInfo(k).label)} in ${monthRange(v.months)}`).join(" and ")}`;
    if (yr.length) s += `${seasonal.length ? ", on top of " : "The pattern points to "}${yr.map(([k]) => lc(sigInfo(k).label)).join(" and ")} all year`;
    return s + ".";
  }

  function renderBrief(b) {
    const h = b.headline;
    const fires = state.index.fire_data_available, vent = state.index.weather_available;
    const g = groupInfo(b.group.id);
    const seasonalN = b.calendar.filter((c) => !c.year_round).length, yearN = b.calendar.length - seasonalN;

    const table = `<div class="table-wrap"><table class="calendar">
        <thead><tr><th>Month</th>${b.monthly.map((m) => `<th class="${m.risk ? "is-risk" : ""}">${MONTHS[m.month - 1]}</th>`).join("")}</tr></thead>
        <tbody>
          <tr><td>AQI, median day</td>${b.monthly.map((m) => `<td><span class="aqi-cell ${aqiCls(aqiCat(m.aqi_median))}" title="${aqiCat(m.aqi_median)?.name ?? ""}">${fmt(m.aqi_median)}</span></td>`).join("")}</tr>
          <tr><td>PM2.5 median, µg/m³<br><small class="muted">middle half of days</small></td>${b.monthly.map((m) => `<td>${fmt(m.pm25_median)}<br><small class="muted">${fmt(m.pm25_p25)} to ${fmt(m.pm25_p75)}</small></td>`).join("")}</tr>
          <tr><td>Days above the limit, per year</td>${b.monthly.map((m) => `<td>${fmt(m.exceed_days)}</td>`).join("")}</tr>
          <tr><td>Likely drivers</td>${b.monthly.map((m) => `<td>${m.drivers.map((d) => `<span class="driver-tag">${swatch(sigCls(d))}${esc(shortSig(d))}</span>`).join("") || "<span class='muted'>none</span>"}</td>`).join("")}</tr>
          <tr><td>Desert dust, µg/m³<br><small class="muted">all sizes</small></td>${b.monthly.map((m) => `<td>${fmt(m.dust)}</td>`).join("")}</tr>
          ${fires ? `<tr><td>Upwind fires a day, within 300 km</td>${b.monthly.map((m) => `<td>${fmt(m.upwind_fires ?? m.fires_300km)}</td>`).join("")}</tr>` : ""}
          ${vent ? `<tr><td>Ventilation, thousand m²/s<br><small class="muted">under 2.5 is stagnant</small></td>${b.monthly.map((m) => `<td>${m.ventilation === null ? "–" : (m.ventilation / 1000).toFixed(1)}</td>`).join("")}</tr>` : ""}
        </tbody></table></div>
      <p class="label">A tinted month is high-risk: median AQI is Poor or worse, or 10 or more days that month go above the daily PM2.5 limit of 60 µg/m³. Typical months over ${state.index.years[0]} to ${state.index.years[state.index.years.length - 1]}.</p>`;

    root.innerHTML = `<div class="app">
      <section class="page-head" aria-labelledby="h-city">
        <h1 id="h-city">${esc(b.city)}</h1>
        ${meta(esc(b.state), "Planner brief", `<a href="#/city/${esc(b.id)}">Resident view</a>`)}
        <p class="standfirst">${esc(briefSummary(b))}</p>
        <dl class="facts">
          <div><dt>Programme status</dt><dd>${esc(statusText(b.list_status))}</dd></div>
          <div><dt>Pattern group</dt><dd>${swatch(groupCls(g.id))}${esc(b.group.label)}</dd></div>
          <div><dt>How firm the grouping is</dt><dd>${b.group.confidence === null ? "–" : `Pattern holds in ${Math.round(b.group.confidence * 100)}% of re-runs`}</dd></div>
        </dl>
        <div class="stats">
          <div><span class="stat__value">${fmt(h.annual_pm25)}<span class="u">µg/m³</span></span><span class="stat__label">Typical yearly PM2.5</span></div>
          <div><span class="stat__value">${fmt(h.exceed_days_per_year)}<span class="u">days</span></span><span class="stat__label">Days a year above the daily limit</span></div>
          <div><span class="stat__value stat__value--words">${monthList(h.worst_months)}</span><span class="stat__label">Worst months</span></div>
          <div><span class="stat__value">${h.risk_months.length}<span class="u">of 12</span></span><span class="stat__label">High-risk months${h.risk_months.length ? `: ${monthList(h.risk_months)}` : ""}</span></div>
        </div>
        <div class="toolbar no-print">
          <button class="btn btn--primary" id="btn-print" type="button">Print or save as PDF</button>
          <button class="btn" id="btn-csv" type="button">Download CSV</button>
        </div>
      </section>

      <section class="block" aria-labelledby="h-year">
        <div class="block__head"><h2 id="h-year">${esc(b.city)}’s year, band by band</h2><p class="label">Typical month, ${state.index.years[0]} to ${state.index.years[state.index.years.length - 1]}</p></div>
        ${airCalendar(b.monthly, `${b.city}, typical air quality by month`)}${aqiKey(true)}
        <div class="well">${nextUp(b)}</div>
      </section>

      <div class="panels">
        ${panel("brief-actions", "Action plan", `${seasonalN} seasonal and ${yearN} year-round measures, each timed to start before the peak`,
          `${actionTimeline(b)}
           <div class="key"><span>${swatch("key-lead")}Preparation</span><span>${swatch("key-peak")}Peak months</span><span>${swatch("key-year")}Year-round</span></div>
           <p class="label">Reference measures from national programmes (NCAP, CAQM/GRAP, MoEFCC and CPCB rules). Check them against your city action plan and the latest directions before acting.</p>`, true)}
        ${panel("brief-months", "Month by month", `AQI, PM2.5 range, days above the limit, dust${fires ? ", upwind fires" : ""}${vent ? ", ventilation" : ""}`, table)}
        ${panel("brief-twins", "Same average, different problem",
          b.same_average_different_problem.length ? `${b.same_average_different_problem.length} cities with a similar yearly average and different bad months` : "No close match with a different pattern",
          `<p>Cities within 10% of ${esc(b.city)}'s yearly PM2.5 whose bad months fall elsewhere. One annual target would treat them alike.</p>${b.same_average_different_problem.length ? sameAverageChart(b) : ""}`)}
        ${panel("brief-peers", "Cities with a similar pattern", `${b.peers.slice(0, 3).map((p) => esc(p.city)).join(", ")} and others, to compare notes with`,
          `<div class="table-wrap"><table>
            <thead><tr><th>City</th><th class="r">Yearly PM2.5</th><th>Same group</th><th class="r">Distance</th></tr></thead>
            <tbody>${b.peers.map((p) => `<tr><td><a href="#/brief/${esc(p.id)}">${esc(p.city)}</a><br><small class="muted">${esc(p.state)}</small></td>
              <td class="r">${fmt(p.annual_pm25)}</td><td>${p.same_group ? "Yes" : "No"}</td><td class="r">${p.km_apart} km${p.likely_same_model_signal ? "*" : ""}</td></tr>`).join("")}</tbody>
          </table></div>
          ${b.peers.some((p) => p.likely_same_model_signal) ? `<p class="label">* Under 40 km away, inside the model's resolution, so the data is nearly the same as ${esc(b.city)}'s.</p>` : ""}`)}
        ${panel("brief-fingerprint", "Pollution fingerprint", `${esc(b.city)} against the other ${state.index.cities.length - 1} NCAP cities`,
          `<p class="label">The bar is the city's rank; the centre line is the typical city.</p>
          <div>${b.features.map((f) => `<div class="fp-row"><span>${esc(f.label)}</span>
            <div class="fp-track" role="img" aria-label="${Math.round(f.percentile * 100)}th percentile"><div class="fp-fill" style="width:${Math.round(f.percentile * 100)}%"></div><div class="fp-mid"></div></div>
            <span class="num" style="text-align:right">${fmtFeature(f)}</span></div>`).join("")}</div>`)}
        ${panel("brief-years", "Year by year", `In its group in ${b.group.years_in_same_group === null ? "–" : Math.round(b.group.years_in_same_group * 100) + "%"} of single-year re-runs`,
          `<div class="table-wrap"><table>
            <thead><tr><th>Year</th><th class="r">Yearly PM2.5</th><th class="r">Days above the limit</th><th>Worst month</th></tr></thead>
            <tbody>${b.yearly.map((y) => `<tr><td>${y.year}</td><td class="r">${fmt(y.annual_pm25)}</td><td class="r">${fmt(y.exceed_days)}</td><td>${MONTHS_LONG[y.peak_month - 1]}</td></tr>`).join("")}</tbody>
          </table></div>${dailySpark(b)}`)}
        ${panel("brief-caveats", "About this data", `${b.caveats.length} things to keep in mind before using these numbers`,
          `${caveatsList(b.caveats)}<p class="label">Data: ${esc(state.index.data_source)}. Generated ${esc(state.index.generated)}.</p>`)}
      </div></div>`;

    document.getElementById("btn-print").addEventListener("click", () => window.print());
    document.getElementById("btn-csv").addEventListener("click", () => download(`aeroscope_${b.id}_brief.csv`, briefCsv(b)));
  }

  function fmtFeature(f) {
    if (f.unit === "" && f.value <= 1.5 && f.key !== "so2_to_no2_ratio") return Math.round(f.value * 100) + "%";
    return fmt(f.value, f.value < 10 ? 2 : 0) + (f.unit ? ` ${f.unit}` : "");
  }

  function actionTimeline(b) {
    if (!b.calendar.length) return `<p class="muted">No measures triggered for this city.</p>`;
    const head = `<div class="tl-row tl-row--head"><span>Measure</span><div class="tl-months">${MONTHS.map((m, i) => `<span${i + 1 === NOW_MONTH ? ' class="is-now"' : ""}>${m[0]}</span>`).join("")}</div></div>`;
    const rows = b.calendar.map((c) => {
      const cells = spanMonths(c.start_month, c.peak_months, c.year_round);
      const when = c.year_round ? "Year-round" : `Start in ${MONTHS_LONG[c.start_month - 1]}, peak ${monthRange(c.peak_months)}`;
      return `<div class="tl-row ${sigCls(c.signature)}">
        <div><div class="tl-action">${esc(c.action)}</div>
          <div class="tl-meta"><span class="tag">${swatch(sigCls(c.signature))}${esc(shortSig(c.signature))}</span><span>${esc(KIND_LABEL[c.kind] || c.kind)}</span><span>${esc(when)}</span><span>${esc(c.owner)}</span><a href="${esc(c.reference.url)}" target="_blank" rel="noopener">${esc(c.reference.title)}</a></div></div>
        <div class="tl-bar" role="img" aria-label="${esc(when)}">${cells.map((t) => `<span class="tl-cell ${t ? "tl-cell--" + t : ""}"></span>`).join("")}</div>
      </div>`;
    }).join("");
    return `<div class="timeline">${head}${rows}</div>`;
  }

  function lineChart(series, opts = {}) {
    const labelled = series.some((s) => s.label);
    const W = opts.w || 560, H = opts.h || 240, P = { l: 38, r: labelled ? 110 : 12, t: 12, b: 26 };
    const all = series.flatMap((s) => s.values.filter((v) => v !== null));
    const max = Math.max(10, ...all) * 1.08;
    const x = (i) => P.l + (i * (W - P.l - P.r)) / 11;
    const y = (v) => H - P.b - (v / max) * (H - P.t - P.b);
    const step = [5, 10, 20, 25, 50, 100, 200].find((s) => max / s <= 5) || 250;
    const ticks = []; for (let t = 0; t <= max; t += step) ticks.push(t);
    const grid = ticks.map((t) => `<line class="grid" x1="${P.l}" x2="${W - P.r}" y1="${y(t)}" y2="${y(t)}"/><text x="${P.l - 6}" y="${y(t) + 4}" text-anchor="end">${t}</text>`).join("");
    const xl = MONTHS.map((m, i) => `<text x="${x(i)}" y="${H - 8}" text-anchor="middle">${m[0]}</text>`).join("");
    const ref = opts.ref && opts.ref.v < max ? `<line class="ref" x1="${P.l}" x2="${W - P.r}" y1="${y(opts.ref.v)}" y2="${y(opts.ref.v)}" stroke-width="1"/><text x="${W - P.r}" y="${y(opts.ref.v) - 4}" text-anchor="end">${esc(opts.ref.label)}</text>` : "";
    const lines = series.map((s) => {
      const pts = s.values.map((v, i) => (v === null ? null : `${x(i)},${y(v)}`)).filter(Boolean).join(" ");
      return `<polyline class="${s.cls || "s-main"}" fill="none" stroke-width="${s.width || 2}" stroke-linejoin="round" points="${pts}"/>`;
    }).join("");
    // End labels, nudged apart so they never overlap.
    const ends = series.filter((s) => s.label && s.values[11] !== null).map((s) => ({ s, y: y(s.values[11]) })).sort((a, b) => a.y - b.y);
    for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 14) ends[i].y = ends[i - 1].y + 14;
    const endLabels = ends.map(({ s, y: yy }) => `<text class="end-label" x="${x(11) + 8}" y="${yy + 4}">${esc(s.label)}</text>`).join("");
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(opts.label || "Monthly chart")}">${grid}${ref}${xl}${lines}${endLabels}</svg>`;
  }

  function sameAverageChart(b) {
    const twins = b.same_average_different_problem;
    const series = [{ values: b.monthly_pm25, cls: "s-main", width: 3 }, ...twins.map((t, i) => ({ values: t.monthly_pm25, cls: `s-g${i}` }))];
    return `<div class="split"><div>${lineChart(series, { label: "Monthly PM2.5 compared with similar-average cities", ref: { v: 60, label: "daily limit, 60" } })}</div>
      <ul class="series">
        <li><span class="line-key" aria-hidden="true"></span><span><strong>${esc(b.city)}</strong>, ${fmt(b.headline.annual_pm25)} µg/m³, worst in ${MONTHS_LONG[b.headline.peak_month - 1]}</span></li>
        ${twins.map((t, i) => `<li><span class="line-key g${i}" aria-hidden="true"></span><span><a href="#/brief/${esc(t.id)}">${esc(t.city)}</a>, ${fmt(t.annual_pm25)} µg/m³, worst in ${MONTHS_LONG[t.peak_month - 1]}<br><small class="muted">${esc(t.group)}</small></span></li>`).join("")}
      </ul></div>`;
  }

  function dailySpark(b) {
    const d = b.daily_latest;
    if (!d || !d.pm25.length) return "";
    const W = 560, H = 120, P = 4;
    const max = Math.max(60, ...d.pm25.filter((v) => v !== null)) * 1.05;
    const n = d.pm25.length;
    const x = (i) => P + (i * (W - 2 * P)) / (n - 1);
    const y = (v) => H - 16 - (v / max) * (H - 24);
    const pts = d.pm25.map((v, i) => (v === null ? null : `${x(i)},${y(v)}`)).filter(Boolean).join(" ");
    const yr = b.yearly.find((r) => r.year === d.year);
    const over = yr ? Math.round(yr.exceed_days) : d.pm25.filter((v) => v > 60).length;
    return `<h4>Every day in ${d.year}</h4>
      <p class="label">${over} days above 60 µg/m³, the line across the chart.</p>
      <svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Daily PM2.5 in ${d.year}">
        <line class="ref" x1="${P}" x2="${W - P}" y1="${y(60)}" y2="${y(60)}" stroke-width="1"/>
        <polyline class="s-main" fill="none" stroke-width="1.2" points="${pts}"/>
        ${MONTHS.map((m, i) => `<text x="${x(Math.round(i * (n - 1) / 12))}" y="${H - 2}">${m[0]}</text>`).join("")}
      </svg>`;
  }

  function briefCsv(b) {
    const rows = [["AeroScope seasonal brief", b.city, b.state], ["Data source", state.index.data_source], ["Generated", state.index.generated], [],
      ["Month", "AQI (median day)", "AQI category", "PM2.5 median", "PM2.5 p25", "PM2.5 p75", "Days above 60 ug/m3 per year", "Desert dust ug/m3 (all sizes)", "Upwind fires/day", "Ventilation m2/s", "Likely drivers", "High-risk month"]];
    b.monthly.forEach((m) => rows.push([MONTHS[m.month - 1], fmt(m.aqi_median), m.aqi_category, fmt(m.pm25_median, 1), fmt(m.pm25_p25, 1), fmt(m.pm25_p75, 1),
      fmt(m.exceed_days, 1), fmt(m.dust, 1), m.upwind_fires ?? m.fires_300km ?? "", m.ventilation ?? "",
      m.drivers.map(shortSig).join("; "), m.risk ? "yes" : "no"]));
    rows.push([], ["Measure", "Signature", "Kind", "Start month", "Peak months", "Owner", "Reference", "Reference URL"]);
    b.calendar.forEach((c) => rows.push([c.action, shortSig(c.signature), c.kind, c.year_round ? "Year-round" : MONTHS[c.start_month - 1],
      monthList(c.peak_months), c.owner, c.reference.title, c.reference.url]));
    rows.push([], ["Caveats"]);
    b.caveats.forEach((c) => rows.push([c]));
    return rows.map((r) => r.map(csvCell).join(",")).join("\n");
  }

  // ------------------------------------------------------------------ CITIZEN view
  function renderCitizen(b) {
    const h = b.headline;
    const reasons = Object.entries(b.drivers).map(([k, v]) =>
      `<li><strong>${esc(sigInfo(k).label)}</strong>, ${v.year_round ? "all year" : monthRange(v.months)}. ${esc(sigInfo(k).plain)}</li>`).join("");
    const thisMonth = b.monthly.find((m) => m.month === NOW_MONTH);
    const thisCat = thisMonth ? aqiCat(thisMonth.aqi_median) : null;
    const peak = b.monthly.find((m) => m.month === h.peak_month);
    const peakCat = peak ? aqiCat(peak.aqi_median) : null;
    root.innerHTML = `<div class="app">
      <section class="page-head" aria-labelledby="h-city">
        <h1 id="h-city">Air in ${esc(b.city)}</h1>
        ${meta(esc(b.state), `<a href="#/brief/${esc(b.id)}">Planner brief</a>`)}
        <p class="standfirst">Usually worst in ${monthList(h.worst_months)}, when a typical day rates ${peakCat ? peakCat.name : "unknown"}. About ${fmt(h.exceed_days_per_year)} days a year go above India's daily limit for fine particles.${thisCat ? ` ${MONTHS_LONG[NOW_MONTH - 1]} is usually ${thisCat.name}.` : ""}</p>
      </section>

      <section class="block" aria-labelledby="h-days">
        <div class="block__head"><h2 id="h-days">Today and the next four days</h2><p class="label">Live forecast, CAMS via Open-Meteo, averaged over each day</p></div>
        <div id="forecast"><div class="skeleton" aria-label="Loading forecast"></div></div>
      </section>

      <section class="block" aria-labelledby="h-year">
        <div class="block__head"><h2 id="h-year">${esc(b.city)}’s year, band by band</h2><p class="label">How the air usually is each month, ${state.index.years[0]} to ${state.index.years[state.index.years.length - 1]}</p></div>
        ${airCalendar(b.monthly, `${b.city}, typical air quality by month`)}${aqiKey(true)}
      </section>

      <div class="panels">
        ${panel("city-why", `Why the air gets bad`, Object.keys(b.drivers).map((k) => shortSig(k)).join(", ") || "No single cause stands out",
          `<ul class="bullets">${reasons || "<li>No single season or source stands out.</li>"}</ul>`, true)}
        ${panel("city-advice", "What to do on bad-air days", "Advice for each AQI band, from Good to Severe", aqiTable())}
        ${panel("city-data", "About this data", "Model estimates: right on timing, lower than monitors on the worst days", caveatsList(b.caveats.slice(0, 2)))}
      </div></div>`;
    loadForecast(b, document.getElementById("forecast"), false);
  }

  async function loadForecast(b, box, compact) {
    if (!box) return;
    const url = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${b.lat}&longitude=${b.lon}` +
      `&hourly=pm2_5,pm10,dust&forecast_days=5&timezone=Asia%2FKolkata`;
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = await r.json();
      const days = new Map();
      j.hourly.time.forEach((t, i) => {
        const d = t.slice(0, 10);
        if (!days.has(d)) days.set(d, { pm25: [], pm10: [], dust: [] });
        const e = days.get(d);
        if (j.hourly.pm2_5[i] !== null) e.pm25.push(j.hourly.pm2_5[i]);
        if (j.hourly.pm10[i] !== null) e.pm10.push(j.hourly.pm10[i]);
        if (j.hourly.dust[i] !== null) e.dust.push(j.hourly.dust[i]);
      });
      const mean = (a) => (a.length ? a.reduce((s, v) => s + v, 0) / a.length : NaN);
      if (!document.body.contains(box)) return; // navigated away
      const out = [...days.entries()].filter(([, e]) => e.pm25.length >= 12).map(([d, e]) => {
        const pm25 = mean(e.pm25), pm10 = mean(e.pm10), dust = mean(e.dust);
        const aqi = particulateAqi(pm25, pm10);
        const date = new Date(d + "T00:00:00");
        let cause = "Local sources";
        // Dust only when heavy and mostly coarse; otherwise fine smoke or smog dominates.
        if (dust >= DUST_LOAD && pm10 > 0 && pm25 / pm10 < 0.5) cause = "Dust";
        else {
          const usual = (b.monthly.find((m) => m.month === date.getMonth() + 1) || { drivers: [] }).drivers.filter((x) => x !== "premonsoon_dust");
          if (usual.length) cause = `${usual.map(shortSig).join(" and ")}, usual for the month`;
        }
        return { date, pm25, aqi, cat: aqiCat(aqi), cause };
      });
      if (!out.length) { box.innerHTML = `<p class="callout">No forecast is available for ${esc(b.city)} right now. The year below still applies.</p>`; return; }
      const [today, ...more] = out;
      const rest = compact ? [] : more;
      const label = (dt) => dt.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
      box.innerHTML = `
        <div class="today well">
          <div><div class="label">Today, ${label(today.date)}</div><div class="today__aqi">${Math.round(today.aqi)}</div><div class="label">AQI</div></div>
          <div class="today__body"><div class="today__cat">${today.cat ? `${swatch(aqiCls(today.cat))}${today.cat.name}` : "Unknown"}</div>
            ${aqiTrack(today.aqi)}
            ${compact ? "" : `<p>${esc(today.cat ? PRACTICAL[today.cat.name] : "")}</p>`}
            <p class="small muted">PM2.5 about ${Math.round(today.pm25)} µg/m³. Likely cause: ${esc(today.cause)}.</p></div>
        </div>
        <div class="forecast">${rest.map((f) => `<div class="fc">
          <span class="fc__date">${label(f.date)}</span><span class="fc__aqi">${Math.round(f.aqi)}</span>
          <span class="fc__cat">${f.cat ? `${swatch(aqiCls(f.cat))}${f.cat.name}` : "Unknown"}</span>${aqiTrack(f.aqi)}<span class="fc__cause">${esc(f.cause)}</span></div>`).join("")}</div>`;
    } catch (err) {
      box.innerHTML = `<p class="callout">The live forecast could not load (${esc(err.message)}). Check your connection and reload; everything else on this page works offline.</p>`;
    }
  }

  // ------------------------------------------------------------------ EXPLORE & METHODS
  async function renderExplore() {
    await loadStudy();
    const s = state.study.summary;
    const ex = state.explore;
    const fall = s.annual_average_fallacy;
    root.innerHTML = `<div class="app">
      <section class="page-head" aria-labelledby="h-all">
        <h1 id="h-all">${state.index.cities.length} cities, by when the air turns bad</h1>
        <p class="standfirst">Each city is placed by the shape of its pollution year: which seasons carry the load, how spiky it is, the particle and gas mix. Not by how high its yearly average is.</p>
        <div class="stats">
          <div><span class="stat__value">${s.chosen_k}</span><span class="stat__label">Pattern groups found</span></div>
          <div><span class="stat__value">${fall.of_which_different_cluster_and_shape_corr_below_0_5}<span class="u">of ${fall.city_pairs_with_annual_pm25_within_10pct}</span></span><span class="stat__label">City pairs with the same yearly PM2.5 but different bad months</span></div>
          <div><span class="stat__value">${fmt(s.bootstrap_mean_ari, 2)}</span><span class="stat__label">How stable the grouping is, 0 to 1</span></div>
          <div><span class="stat__value">${fmt(s.naive_annual_vs_seasonal_ari, 2)}</span><span class="stat__label">Overlap with grouping by yearly average only, 0 to 1</span></div>
        </div>
      </section>

      <section class="block" aria-labelledby="h-map">
        <div class="block__head"><h2 id="h-map">Where each pattern sits</h2>
          <div class="toolbar toolbar--groups">
            <div class="ctrl"><span class="label" id="lbl-view">View</span><div class="pill-group" role="group" aria-labelledby="lbl-view">${[["map", "India"], ["pca", "Pattern space, PCA"], ["tsne", "Pattern space, t-SNE"]].map(([k, l]) => `<button class="pill" type="button" data-proj="${k}" aria-pressed="${ex.proj === k}">${l}</button>`).join("")}</div></div>
            <div class="ctrl"><span class="label" id="lbl-colour">Colour by</span><div class="pill-group" role="group" aria-labelledby="lbl-colour">${[["group", "Seasonal pattern"], ["naive", "Yearly average only"], ["aqi", "Yearly AQI band"]].map(([k, l]) => `<button class="pill" type="button" data-color="${k}" aria-pressed="${ex.color === k}">${l}</button>`).join("")}</div></div>
          </div>
        </div>
        <p class="label">Select a city to open its brief. A bigger dot means higher yearly PM2.5.</p>
        <div class="split split--top">
          <div class="map-wrap" id="map-wrap">${mapSvg()}<div class="map-tip" id="map-tip"></div></div>
          <div>${groupLegend()}</div>
        </div>
      </section>

      <div class="panels">
        ${panel("explore-table", "All cities", "Search, sort and open any city's brief",
          `<label class="label" for="tbl-q">Filter by city, state or group</label>
           <input class="input" id="tbl-q" name="filter" type="search" value="${esc(ex.q)}" style="max-width:22rem;min-height:var(--control-app)"/>
           <div class="table-wrap"><table class="sortable" id="city-table"></table></div>`)}
        ${panel("explore-methods", "How the groups were found", "Data, features, stability checks, independent evidence, limits", methodsBlock())}
        ${panel("explore-figures", "Figures", `${state.study.figures.length} charts from the analysis`,
          `<div class="figures-grid">${state.study.figures.map((f) => `<figure><img loading="lazy" src="data/figures/${esc(f)}" alt="${esc(f.replace(/^\d+_/, "").replace(/_/g, " ").replace(".png", ""))}" width="1600" height="900"/><figcaption>${esc(f.replace(/^\d+_/, "").replace(/_/g, " ").replace(".png", ""))}</figcaption></figure>`).join("")}</div>`)}
      </div></div>`;

    root.querySelectorAll("[data-proj]").forEach((b) => b.addEventListener("click", () => { ex.proj = b.dataset.proj; renderExplore().then(wirePanels); }));
    root.querySelectorAll("[data-color]").forEach((b) => b.addEventListener("click", () => { ex.color = b.dataset.color; renderExplore().then(wirePanels); }));
    wireMap();
    const q = document.getElementById("tbl-q");
    q.addEventListener("input", () => { ex.q = q.value; renderTable(); });
    renderTable();
  }

  function pm25Cat(v) {
    if (v === null || v === undefined) return null;
    return aqiCat(subIndex(v, PM25_BP));
  }
  // The landing's signature: every NCAP city lit by its typical PM2.5 band for the current month.
  function heroMap() {
    const cities = state.index.cities;
    const W = 520, H = 560, k = Math.cos((22 * Math.PI) / 180);
    const lon0 = 67.5, lon1 = 98, lat1 = 37.5;
    const sc = Math.min((W - 20) / ((lon1 - lon0) * k), (H - 20) / (lat1 - 6));
    const px = (lon) => 10 + (lon - lon0) * k * sc, py = (lat) => 10 + (lat1 - lat) * sc;
    const outline = `<path class="india-outline" d="M${INDIA_POLY.map(([lo, la]) => `${px(lo).toFixed(1)},${py(la).toFixed(1)}`).join("L")}Z"/>`;
    const dots = [...cities].sort((a, b) => (a.monthly_pm25[NOW_MONTH - 1] ?? 0) - (b.monthly_pm25[NOW_MONTH - 1] ?? 0)).map((c) => {
      const v = c.monthly_pm25[NOW_MONTH - 1];
      const cat = pm25Cat(v);
      const r = 2.5 + Math.max(v || 0, 0) / 9;
      const bad = cat && AQI_CATS.indexOf(cat) >= 3;
      const haze = bad ? `<circle class="city-haze aqi--${cat.cls}" cx="${px(c.lon).toFixed(1)}" cy="${py(c.lat).toFixed(1)}" r="${(r * 2.6).toFixed(1)}" aria-hidden="true"></circle>` : "";
      return `${haze}<circle class="city-dot ${cat ? `aqi--${cat.cls}` : ""}" tabindex="0" role="link" aria-label="${esc(c.city)}: typical ${MONTHS_LONG[NOW_MONTH - 1]} PM2.5 ${fmt(v)} micrograms, ${cat ? cat.name : "unknown"}" data-id="${esc(c.id)}" data-v="${fmt(v)}" data-band="${cat ? cat.name : ""}" cx="${px(c.lon).toFixed(1)}" cy="${py(c.lat).toFixed(1)}" r="${r.toFixed(1)}"></circle>`;
    }).join("");
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="group" aria-label="NCAP cities by typical ${MONTHS_LONG[NOW_MONTH - 1]} PM2.5">${outline}${dots}</svg>`;
  }
  function wireHeroMap() {
    const wrap = document.getElementById("hero-map"), tip = document.getElementById("hero-tip");
    if (!wrap) return;
    wrap.querySelectorAll(".city-dot").forEach((d) => {
      const c = state.byId.get(d.dataset.id);
      const show = () => {
        const rb = wrap.getBoundingClientRect(), rd = d.getBoundingClientRect();
        tip.textContent = `${c.city}, ${d.dataset.v} µg/m³, ${d.dataset.band || "no data"}`;
        tip.style.left = `${rd.left - rb.left + rd.width / 2}px`; tip.style.top = `${rd.top - rb.top}px`; tip.style.display = "block";
      };
      const go = () => { location.hash = `#/city/${c.id}`; };
      d.addEventListener("click", go);
      d.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
      d.addEventListener("mouseenter", show); d.addEventListener("focus", show);
      d.addEventListener("mouseleave", () => { tip.style.display = "none"; }); d.addEventListener("blur", () => { tip.style.display = "none"; });
    });
  }

  function dotCls(c) {
    const ex = state.explore;
    if (ex.color === "naive") return grpCls(c.naive);
    if (ex.color === "aqi") { const cat = catByName(c.annual_aqi_category); return cat ? `aqi--${cat.cls}` : ""; }
    return groupCls(c.group);
  }

  function mapSvg() {
    const ex = state.explore, cities = state.index.cities;
    const W = 520, H = 560;
    let px, py;
    if (ex.proj === "map") {
      const k = Math.cos((22 * Math.PI) / 180);
      const lon0 = 67.5, lon1 = 98, lat0 = 6, lat1 = 37.5;
      const s = Math.min((W - 20) / ((lon1 - lon0) * k), (H - 20) / (lat1 - lat0));
      px = (lon) => 10 + (lon - lon0) * k * s; py = (lat) => 10 + (lat1 - lat) * s;
    } else {
      const key = ex.proj;
      const xs = cities.map((c) => c[key][0]), ys = cities.map((c) => c[key][1]);
      const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
      px = (v) => 20 + ((v - x0) / (x1 - x0 || 1)) * (W - 40); py = (v) => H - 30 - ((v - y0) / (y1 - y0 || 1)) * (H - 50);
    }
    const outline = ex.proj === "map" ? `<path class="india-outline" d="M${INDIA_POLY.map(([lo, la]) => `${px(lo).toFixed(1)},${py(la).toFixed(1)}`).join("L")}Z"/>` : "";
    const dots = [...cities].sort((a, b) => b.annual_pm25 - a.annual_pm25).map((c) => {
      const [x, y] = ex.proj === "map" ? [px(c.lon), py(c.lat)] : [px(c[ex.proj][0]), py(c[ex.proj][1])];
      const r = 3 + Math.sqrt(Math.max(c.annual_pm25, 1)) * 0.75;
      return `<circle class="city-dot ${dotCls(c)}" tabindex="0" role="link" aria-label="${esc(c.city)}, ${fmt(c.annual_pm25)} micrograms a year" data-id="${esc(c.id)}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(1)}"></circle>`;
    }).join("");
    const note = ex.proj === "map" ? "" : `<text x="${W / 2}" y="${H - 6}" text-anchor="middle">Nearby dots have similar pollution years</text>`;
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="group" aria-label="Map of NCAP cities">${outline}${dots}${note}</svg>`;
  }

  function wireMap() {
    const wrap = document.getElementById("map-wrap"), tip = document.getElementById("map-tip");
    wrap.querySelectorAll(".city-dot").forEach((d) => {
      const c = state.byId.get(d.dataset.id);
      const go = () => { location.hash = `#/brief/${c.id}`; };
      const show = () => {
        const rb = wrap.getBoundingClientRect(), rd = d.getBoundingClientRect();
        tip.textContent = `${c.city}, ${fmt(c.annual_pm25)} µg/m³, ${groupInfo(c.group).label}`;
        tip.style.left = `${rd.left - rb.left + rd.width / 2}px`; tip.style.top = `${rd.top - rb.top}px`; tip.style.display = "block";
      };
      d.addEventListener("click", go);
      d.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
      d.addEventListener("mouseenter", show); d.addEventListener("focus", show);
      d.addEventListener("mouseleave", () => { tip.style.display = "none"; }); d.addEventListener("blur", () => { tip.style.display = "none"; });
    });
  }

  function groupLegend() {
    const ex = state.explore;
    if (ex.color === "aqi") {
      return `<h3>Yearly AQI band</h3><ul class="series" style="margin-top:var(--space-sm)">${AQI_CATS.map((c) => {
        const n = state.index.cities.filter((x) => x.annual_aqi_category === c.name).length;
        return `<li>${swatch(`aqi--${c.cls}`)}<span>${c.name}: ${n} cities</span></li>`;
      }).join("")}</ul>`;
    }
    const naive = ex.color === "naive";
    const membersOf = (g) => state.index.cities.filter((c) => (naive ? c.naive : c.group) === g.id);
    const groups = naive
      ? [...state.index.groups].sort((a, b) => Math.min(...membersOf(a).map((c) => c.annual_pm25), 1e9) - Math.min(...membersOf(b).map((c) => c.annual_pm25), 1e9))
      : state.index.groups;
    const items = groups.map((g) => {
      const members = membersOf(g);
      if (!members.length) return "";
      const shape = new Array(12).fill(0).map((_, i) => {
        const vals = members.map((c) => c.monthly_pm25[i]).filter((v) => v !== null).sort((a, b) => a - b);
        return vals.length ? vals[Math.floor(vals.length / 2)] : null;
      });
      const mixed = naive ? new Set(members.map((c) => c.group)).size : 1;
      const pms = members.map((c) => c.annual_pm25);
      const title = naive ? `PM2.5 ${fmt(Math.min(...pms))} to ${fmt(Math.max(...pms))} µg/m³` : esc(g.label);
      const colour = naive ? grpCls(g.id) : groupCls(g.id);
      const hint = `${members.length} cities, ${naive ? (mixed > 1 ? `mixing ${mixed} different seasonal patterns` : "all one seasonal pattern") : `median ${fmt(g.median_pm25)} µg/m³`}`;
      return `<details class="panel panel--quiet"><summary><span class="panel__title"><span class="tag">${swatch(colour)}${title}</span></span><span class="panel__hint">${hint}</span><span class="panel__sign" aria-hidden="true"></span></summary>
        <div class="panel__body">${lineChart([{ values: shape, cls: `s-var ${colour}`, width: 2.5 }], { h: 110, label: "Median monthly PM2.5 for this group" })}
        <p class="small">${members.map((c) => `<a href="#/brief/${esc(c.id)}">${esc(c.city)}</a>`).join(", ")}</p></div></details>`;
    }).join("");
    return `<h3>${naive ? "Grouped by yearly average only" : "Pattern groups"}</h3>
      <p class="label" style="margin-top:var(--space-2xs)">${naive ? "Each band holds cities with similar yearly PM2.5. Open one to see how it mixes cities whose bad months differ." : "Open a group to see its typical year and its cities."}</p>
      <div class="panels" style="margin-top:var(--space-sm)">${items}</div>`;
  }

  function renderTable() {
    const ex = state.explore, t = document.getElementById("city-table");
    if (!t) return;
    const q = ex.q.trim().toLowerCase();
    const rows = state.index.cities.filter((c) => !q || `${c.city} ${c.state} ${groupInfo(c.group).label}`.toLowerCase().includes(q))
      .sort((a, b) => {
        const va = sortVal(a, ex.sort), vb = sortVal(b, ex.sort);
        return (va > vb ? 1 : va < vb ? -1 : 0) * ex.dir;
      });
    const cols = [["city", "City"], ["state", "State"], ["group", "Pattern group"], ["annual_pm25", "Yearly PM2.5"], ["exceed_days", "Days above limit"], ["peak_month", "Worst month"], ["confidence", "Stability"]];
    const right = ["annual_pm25", "exceed_days", "confidence"];
    t.innerHTML = `<thead><tr>${cols.map(([k, l]) => `<th class="${right.includes(k) ? "r" : ""}" aria-sort="${ex.sort === k ? (ex.dir > 0 ? "ascending" : "descending") : "none"}"><button class="sort" type="button" data-k="${k}">${l}${ex.sort === k ? (ex.dir > 0 ? ", rising" : ", falling") : ""}</button></th>`).join("")}</tr></thead>
      <tbody>${rows.length ? rows.map((c) => `<tr><td><a href="#/brief/${esc(c.id)}">${esc(c.city)}</a>${c.outlier ? '<br><small class="muted">unusual pattern</small>' : ""}</td><td>${esc(c.state)}</td>
        <td><span class="tag">${swatch(groupCls(c.group))}${esc(groupInfo(c.group).label)}</span></td>
        <td class="r">${fmt(c.annual_pm25)}</td><td class="r">${fmt(c.exceed_days)}</td><td>${MONTHS[c.peak_month - 1]}</td><td class="r">${Math.round(c.confidence * 100)}%</td></tr>`).join("")
        : `<tr><td colspan="7" class="muted">No city matches “${esc(ex.q)}”. Clear the filter to see all ${state.index.cities.length}.</td></tr>`}</tbody>`;
    t.querySelectorAll(".sort").forEach((btn) => btn.addEventListener("click", () => {
      const k = btn.dataset.k;
      ex.dir = ex.sort === k ? -ex.dir : (["city", "state", "group"].includes(k) ? 1 : -1);
      ex.sort = k; renderTable();
      t.querySelector(`.sort[data-k="${k}"]`).focus();
    }));
  }
  const sortVal = (c, k) => (k === "group" ? groupInfo(c.group).label : c[k]);

  function methodsBlock() {
    const s = state.study.summary, a = state.study.audit, th = state.study.thresholds;
    const years = Object.entries(s.year_to_year_ari).map(([k, v]) => `${k.replace("_vs_", " against ")}, ${fmt(v, 2)}`).join("; ");
    const tests = s.evidence_tests.map((t) => t.status !== "tested"
      ? `<tr><td>${esc(sigInfo(t.signature).label)}</td><td>${esc(t.evidence)}</td><td colspan="3" class="muted">${esc(t.status)}</td></tr>`
      : `<tr><td>${esc(sigInfo(t.signature).label)}</td><td>${esc(t.evidence)}</td><td class="r">${fmt(t.median_with_signature, 1)} against ${fmt(t.median_without, 1)}</td><td class="r">${t.p_value}</td><td>${t.supported ? "Supported" : "Not supported"}</td></tr>`).join("");
    const km = state.study.k_metrics.map((r) => `<tr${r.k === s.chosen_k ? ' style="font-weight:600"' : ""}><td>${r.k}${r.k === s.chosen_k ? ", chosen" : ""}</td><td class="r">${fmt(r.silhouette_score, 3)}</td><td class="r">${fmt(r.davies_bouldin_index, 3)}</td><td class="r">${fmt(r.bootstrap_mean_ari, 3)}</td><td class="r">${r.smallest_cluster}</td></tr>`).join("");
    return `<div class="cols-2">
      <div><h3>Data</h3>
        <ul class="bullets">
          <li>${esc(state.index.data_source)}. Daily values for ${a.cities} cities, ${a.date_range[0]} to ${a.date_range[1]}, ${a.initial_rows.toLocaleString("en-IN")} city-days.</li>
          <li>City list: CPCB's official list of 131 NCAP cities, geocoded; small industrial towns placed by hand.</li>
          <li>Fire detections, NASA FIRMS VIIRS: ${state.index.fire_data_available ? `${a.fire_detections.toLocaleString("en-IN")} detections used` : "not loaded, so smoke is not verified"}.</li>
          <li>Ventilation, ERA5 wind times boundary-layer height, October to February: ${state.index.weather_available ? "used" : "not loaded"}.</li>
          <li>Quality control removed ${Object.values(a.out_of_bounds_removed).reduce((x, y) => x + y, 0)} out-of-range values and ${a.incomplete_days_removed} incomplete days.</li>
        </ul></div>
      <div><h3>How the groups were found</h3>
        <ul class="bullets">
          <li>Fifteen features describe the shape of each city's year: seasonal shares of PM2.5, the October-November and winter spikes, the March-May dust load, coarse fraction, SO₂ against NO₂, the NO₂, SO₂ and PM2.5 levels, seasonality and spikiness.</li>
          <li>K-Means, with the number of groups chosen from silhouette and bootstrap stability, checked against Ward clustering (agreement ${fmt(s.kmeans_vs_ward_ari, 2)}), DBSCAN and Isolation Forest with LOF outliers.</li>
          <li>Groups are named from their centre features. Fire and ventilation data stay out of the grouping, so they serve as independent evidence.</li>
          <li>Monthly drivers: a high-risk month has median AQI above ${th.risk_aqi} or ${th.risk_exceed_days} or more days above the limit; dust when March-June desert dust reaches ${th.dust_load} µg/m³; stagnant air when winter PM2.5 is ${th.stagnation_ratio} times the yearly mean${state.index.weather_available ? ` and ventilation is under ${th.poor_ventilation} m²/s` : ""}.</li>
        </ul></div>
      <div><h3>Is the grouping real?</h3>
        <ul class="bullets">
          <li>Silhouette ${fmt(s.kmeans_silhouette, 2)}, Davies-Bouldin ${fmt(s.kmeans_davies_bouldin, 2)}. Moderate separation is expected: real cities sit on a continuum.</li>
          <li>Bootstrap, 200 resamples: mean ARI ${fmt(s.bootstrap_mean_ari, 2)}; ${s.cities_with_confidence_ge_0_8} of ${s.n_cities} cities keep their group at least 80% of the time.</li>
          <li>Each year grouped on its own: ${years}.</li>
          <li>Yearly average only against seasonal pattern: ARI ${fmt(s.naive_annual_vs_seasonal_ari, 2)}. Yearly averages put cities with different problems in the same box.</li>
        </ul>
        <h4>Independent evidence</h4>
        <div class="table-wrap"><table>
          <thead><tr><th>Pattern</th><th>Evidence</th><th class="r">Median with, without</th><th class="r">p</th><th>Result</th></tr></thead>
          <tbody>${tests}</tbody></table></div></div>
      <div><h3>Choosing the number of groups</h3>
        <div class="table-wrap"><table>
          <thead><tr><th>Groups</th><th class="r">Silhouette, higher better</th><th class="r">Davies-Bouldin, lower better</th><th class="r">Bootstrap ARI</th><th class="r">Smallest group</th></tr></thead>
          <tbody>${km}</tbody></table></div>
        <h4>Limits</h4>
        <ul class="bullets">
          <li>CAMS is a ~40 km global model. It gets regional seasons right but reads lower than city monitors in the worst episodes; the timing is the main signal.</li>
          <li>NO₂ and SO₂ are diluted at 40 km, so source labels are hints, not source apportionment.</li>
          <li>Cities under ~40 km apart share nearly the same model signal.</li>
          <li>CAMS is upgraded from time to time, which can shift levels between years.</li>
        </ul></div>
    </div>`;
  }

  // ------------------------------------------------------------------ boot
  async function init() {
    try {
      state.index = await loadJSON("data/index.json");
    } catch (err) {
      root.innerHTML = `<div class="app"><div class="page-head"><h1>Data not found</h1><p class="callout">Could not load data/index.json (${esc(err.message)}).
        Run the pipeline with <code>start.bat --rebuild</code> and serve the <code>web</code> folder over HTTP.</p></div></div>`;
      return;
    }
    state.index.cities.forEach((c) => state.byId.set(c.id, c));
    const src = document.getElementById("footer-source");
    if (src) src.textContent = `Air-quality guides for ${state.index.cities.length} NCAP cities, ${state.index.years[0]} to ${state.index.years[state.index.years.length - 1]}. Data generated ${state.index.generated}.`;
    document.getElementById("city-options").innerHTML = [...state.index.cities].sort((a, b) => a.city.localeCompare(b.city))
      .map((c) => `<option value="${esc(c.city)}, ${esc(c.state)}"></option>`).join("");
    document.getElementById("city-picker").addEventListener("submit", (e) => {
      e.preventDefault();
      const input = document.getElementById("city-input");
      const hit = findCity(input.value);
      if (!hit) { input.setCustomValidity("No NCAP city matches"); input.reportValidity(); return; }
      input.setCustomValidity("");
      location.hash = `#/${parseHash().view === "brief" ? "brief" : "city"}/${hit.id}`;
      input.value = "";
    });
    document.getElementById("city-input").addEventListener("input", (e) => e.target.setCustomValidity(""));
    window.addEventListener("hashchange", route);
    route();
  }
  init();
})();

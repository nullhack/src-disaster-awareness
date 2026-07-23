/* =========================================================================
   Disaster Surveillance — Daily Digest dashboard
   Loads ONE daily digest JSON at a time (lazy by date). All aggregations
   are pre-computed in the digest; the browser only filters/renders.
   ========================================================================= */
"use strict";

const SEV_RANK = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
const SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const SEV_COLOR = { CRITICAL: "#7A0019", HIGH: "#E4002B", MEDIUM: "#E8A317", LOW: "#4F7CAC" };
const TYPE_COLOR = {
  Earthquake: "#8B5A2B", Disease: "#7A0019", Flood: "#1F77B4",
  Wildfire: "#E8741E", "Tropical Cyclone": "#0E9594", Other: "#6E6E6E",
};
const typeColor = (t) => TYPE_COLOR[t] || TYPE_COLOR.Other;
// distinct palette for disease pathogens (disease trend panel)
const DISEASE_COLOR = {
  Ebola: "#7A0019", Nipah: "#B4009E", Cholera: "#0E7C7B",
  Mpox: "#C2410C", Dengue: "#1D4ED8",
  Diphtheria: "#4C1D95", Hantavirus: "#15803D", MERS: "#B45309",
  Measles: "#BE185D", "Unknown pathogen": "#6E6E6E", Other: "#6E6E6E",
};
const diseaseColor = (d) => DISEASE_COLOR[d] || DISEASE_COLOR.Other;

/* ISO2 -> [lat, lon] centroids. Approximate country-level for the map. */
const CENTROIDS = {
  AF:[33.9,67.7],AL:[41.2,20.2],DZ:[28.0,1.7],AD:[42.5,1.5],AO:[-11.2,17.9],
  AR:[-38.4,-63.6],AM:[40.1,45.0],AU:[-25.3,133.8],AT:[47.5,14.6],AZ:[40.1,47.6],
  BD:[23.7,90.4],BY:[53.7,27.9],BE:[50.5,4.5],BZ:[17.2,-88.5],BJ:[9.3,2.3],
  BT:[27.5,90.4],BO:[-16.3,-63.6],BA:[43.9,17.7],BW:[-22.3,24.7],BR:[-14.2,-51.9],
  BN:[4.5,114.7],BG:[42.7,25.5],BF:[12.2,-1.6],BI:[-3.4,29.9],KH:[12.6,104.9],
  CM:[7.4,12.4],CA:[56.1,-106.3],CV:[16.0,-24.0],CF:[6.6,20.9],TD:[15.5,18.7],
  CL:[-35.7,-71.5],CN:[35.9,104.2],CO:[4.6,-74.3],KM:[-11.9,43.9],CG:[-0.7,15.8],
  CD:[-4.0,21.8],CR:[9.7,-83.8],CI:[7.5,-5.5],HR:[45.1,15.2],CU:[21.5,-77.8],
  CY:[35.1,33.4],CZ:[49.8,15.5],DK:[56.3,9.5],DJ:[11.8,42.6],DO:[18.7,-70.2],
  EC:[-1.8,-78.2],EG:[26.8,30.8],SV:[13.8,-88.9],GQ:[1.7,10.3],ER:[15.2,39.8],
  EE:[58.6,25.0],ET:[9.1,40.5],FJ:[-17.7,178.1],FI:[61.9,25.7],FR:[46.2,2.2],
  GA:[-0.8,11.6],GM:[13.4,-15.3],GE:[42.3,43.4],DE:[51.2,10.5],GH:[7.9,-1.0],
  GR:[39.1,21.8],GL:[71.7,-42.6],GT:[15.8,-90.2],GN:[9.9,-9.7],GW:[12.0,-15.2],
  GY:[4.9,-58.9],HT:[18.9,-72.3],HN:[14.6,-86.2],HK:[22.3,114.2],HU:[47.2,19.5],
  IS:[64.9,-19.0],IN:[20.6,79.0],ID:[-0.8,113.9],IR:[32.4,53.7],IQ:[33.2,43.7],
  IE:[53.1,-7.7],IL:[31.0,34.9],IT:[41.9,12.6],JM:[18.1,-77.3],JP:[36.2,138.3],
  JO:[30.6,36.2],KZ:[48.0,66.9],KE:[0.0,37.9],KP:[40.3,127.5],KR:[35.9,127.8],
  KW:[29.3,47.5],KG:[41.2,74.8],LA:[19.9,102.5],LV:[56.9,24.6],LB:[33.9,35.9],
  LS:[-29.6,28.2],LR:[6.4,-9.4],LY:[26.3,17.2],LI:[47.2,9.6],LT:[55.2,23.9],
  LU:[49.8,6.1],MO:[22.2,113.5],MK:[41.6,21.7],MG:[-18.8,46.9],MW:[-13.3,34.3],
  MY:[4.2,109.5],MV:[3.2,73.2],ML:[17.6,-4.0],MT:[35.9,14.4],MR:[21.0,-10.9],
  MU:[-20.3,57.6],MX:[23.6,-102.6],MD:[47.4,28.4],MN:[46.9,103.8],ME:[42.7,19.4],
  MA:[31.8,-7.1],MZ:[-18.7,35.5],MM:[21.9,95.9],NA:[-22.6,18.5],NP:[28.4,84.1],
  NL:[52.1,5.3],NZ:[-40.9,174.9],NI:[12.9,-85.2],NE:[17.6,8.1],NG:[9.1,8.7],
  MK:[41.6,21.7],NO:[60.5,8.5],OM:[21.5,55.9],PK:[30.4,69.3],PS:[31.9,35.2],
  PA:[8.5,-80.8],PG:[-6.3,143.9],PY:[-23.4,-58.4],PE:[-9.2,-75.0],PH:[12.9,121.8],
  PL:[51.9,19.1],PT:[39.4,-8.2],PR:[18.2,-66.6],QA:[25.4,51.2],RO:[45.9,24.97],
  RU:[61.5,105.3],RW:[-1.9,29.9],SA:[23.9,45.1],SN:[14.5,-14.5],RS:[44.0,21.0],
  SC:[-4.7,55.5],SL:[8.5,-11.8],SG:[1.4,103.8],SK:[48.7,19.7],SI:[46.2,14.99],
  SO:[5.2,46.2],ZA:[-30.6,22.9],SS:[6.9,31.3],ES:[40.5,-3.7],LK:[7.9,80.8],
  SD:[12.9,30.2],SR:[3.9,-56.0],SZ:[-26.5,31.5],SE:[60.1,18.6],CH:[46.8,8.2],
  SY:[34.8,38.9],TW:[23.7,121.0],TJ:[38.9,71.3],TZ:[-6.4,34.9],TH:[15.9,100.99],
  TL:[-8.9,125.7],TG:[8.6,0.8],TO:[-21.2,-175.2],TT:[10.7,-61.2],TN:[33.9,9.5],
  TR:[38.9,35.2],TM:[38.97,59.6],UG:[1.4,32.3],UA:[48.4,31.2],AE:[23.4,53.8],
  GB:[55.4,-3.4],US:[37.1,-95.7],UY:[-32.5,-55.8],UZ:[41.4,64.6],VU:[-16.4,167.9],
  VE:[6.4,-66.6],VN:[14.1,108.3],YE:[15.6,48.5],ZM:[-13.1,27.8],ZW:[-19.0,29.2],
  GS:[-54.4,-36.6],GR:[39.1,21.8],EH:[24.2,-12.9],
};

/* ---------- state ---------- */
const STATE = {
  manifest: null,
  digest: null,
  digestDates: [],       // available digest report dates (sorted oldest → newest)
  digestByDate: {},      // date -> manifest entry
  digestDate: "",        // currently loaded digest date
  dpView: { y: 2026, m: 6 }, // calendar month being viewed (UTC, 0-based month)
  aggIndex: null,       // {windows, default_window, files} from data/agg/index.json
  agg: {},              // cache: window -> aggregation object (cumulative history)
  filters: { severities: new Set(["CRITICAL", "HIGH", "MEDIUM", "LOW"]), types: new Set(), regions: new Set(), q: "" },
  sort: { key: "severity", dir: "asc" },
  tab: "watchlist",
  trend: { window: "30", metric: "n" }, // metric: n(news)|e(events); two panels: disease(by pathogen) + geo(by kind)
  kpiSel: { sev: null, sort: null, type: null }, // explicit per-axis KPI selection (null = none)
};
if (typeof window !== "undefined") window.STATE = STATE; // debug hook

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

/* ---------- entry point ---------- */
(async function init() {
  try {
    STATE.manifest = await fetchJSON("data/index.json");
    fillDigestPicker();
    if (!STATE.manifest.digests.length) throw new Error("No digests available.");

    // Aggregations are a SEPARATE, global historical artifact (not per-digest).
    // Preload all of them once; the timeline reads from this cache.
    try {
      STATE.aggIndex = await fetchJSON("data/agg/index.json");
      STATE.trend.window = String(STATE.aggIndex.default_window || STATE.aggIndex.windows[0] || "30");
      const wins = STATE.aggIndex.windows || [];
      STATE.agg = {};
      await Promise.all(wins.map(async (w) => { STATE.agg[w] = await fetchJSON(`data/agg/${STATE.aggIndex.files[w] || (w + ".json")}`); }));
    } catch (e) { console.warn("Aggregations unavailable, timeline disabled:", e.message); }
    populateTrendWindow();
    updateTrendSegs();
    $("#trendTitle").textContent = `${STATE.trend.window}-day trend`;

    const latest = STATE.manifest.digests[STATE.manifest.digests.length - 1];
    await loadDigest(latest.file);
    selectTab(STATE.tab); // sync tab DOM to default (active watchlist)
  } catch (err) {
    showError(`Failed to load: ${err.message}`);
  }
  wireGlobalEvents();
})();

async function fetchJSON(url) {
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${url} → HTTP ${r.status}`);
  return r.json();
}

function fillDigestPicker() {
  const digs = STATE.manifest.digests; // oldest → newest
  STATE.digestDates = digs.map((d) => d.date);
  STATE.digestByDate = Object.fromEntries(digs.map((d) => [d.date, d]));
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DOW = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
const isoOf = (y, m, d) => `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;

function renderCal() {
  const { y, m } = STATE.dpView;
  const firstDow = (new Date(Date.UTC(y, m, 1)).getUTCDay() + 6) % 7; // Monday-first
  const dim = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
  let cells = "";
  for (let i = 0; i < firstDow; i++) cells += `<div class="dp__cell dp__cell--blank"></div>`;
  for (let d = 1; d <= dim; d++) {
    const iso = isoOf(y, m, d);
    const avail = !!STATE.digestByDate[iso];
    const sel = iso === STATE.digestDate;
    cells += `<button class="dp__cell${avail ? " dp__cell--avail" : ""}${sel ? " dp__cell--sel" : ""}" data-date="${iso}"${avail ? "" : " disabled"}>${d}</button>`;
  }
  $("#dpCal").innerHTML =
    `<div class="dp__cal-head">
       <button class="dp__cal-nav" data-nav="-1" type="button" aria-label="Previous month">‹</button>
       <span>${MONTHS[m]} ${y}</span>
       <button class="dp__cal-nav" data-nav="1" type="button" aria-label="Next month">›</button>
     </div>
     <div class="dp__cal-grid">${DOW.map((d) => `<div class="dp__dow">${d}</div>`).join("")}${cells}</div>`;
}
function openCal() {
  const base = STATE.digestDate ? new Date(STATE.digestDate + "T00:00:00Z") : new Date();
  STATE.dpView = { y: base.getUTCFullYear(), m: base.getUTCMonth() };
  renderCal();
  $("#dpCal").hidden = false;
  $("#dpLabel").setAttribute("aria-expanded", "true");
}
function closeCal() {
  $("#dpCal").hidden = true;
  $("#dpLabel").setAttribute("aria-expanded", "false");
}
function toggleCal() { $("#dpCal").hidden ? openCal() : closeCal(); }

const tsOf = (iso) => new Date(iso + "T00:00:00Z").getTime();

function nearestDigestDate(iso) {
  const dates = STATE.digestDates;
  if (!dates.length) return null;
  if (dates.includes(iso)) return iso;
  const t = tsOf(iso);
  let best = dates[0], bestDiff = Math.abs(t - tsOf(best));
  for (const d of dates) {
    const diff = Math.abs(t - tsOf(d));
    if (diff < bestDiff) { bestDiff = diff; best = d; }
  }
  return best;
}

async function loadDigestByDate(iso) {
  const nearest = nearestDigestDate(iso);
  if (!nearest) return;
  if (nearest !== iso) showToast(`No digest for ${iso} — showing nearest: ${nearest}`);
  const entry = STATE.digestByDate[nearest];
  if (entry) {
    try { await loadDigest(entry.file); }
    catch (err) { showError(err.message); }
  }
}

function stepDigest(dir) {
  const idx = STATE.digestDates.indexOf(STATE.digestDate);
  if (idx < 0) return;
  const ni = idx + dir;
  if (ni < 0 || ni >= STATE.digestDates.length) return;
  loadDigestByDate(STATE.digestDates[ni]);
}

function refreshDateControls() {
  const idx = STATE.digestDates.indexOf(STATE.digestDate);
  $("#dpLabel").textContent = STATE.digestDate ? fmtDate(STATE.digestDate) : "—";
  $("#dpPrev").disabled = idx <= 0;
  $("#dpNext").disabled = idx < 0 || idx >= STATE.digestDates.length - 1;
  const entry = STATE.digestByDate[STATE.digestDate];
  $("#digestMeta").textContent = entry
    ? `${entry.reportable_total} active · ${entry.critical} critical · ${entry.disease_outbreaks} disease`
    : "";
  const reportLink = $("#dpReport");
  if (STATE.digestDate) {
    const [y, m] = STATE.digestDate.split("-");
    reportLink.href = `https://github.com/nullhack/src-disaster-awareness/blob/gh-pages/reports/${y}/${m}/${y}${m}${STATE.digestDate.slice(8)}.md`;
    reportLink.hidden = false;
  } else {
    reportLink.hidden = true;
  }
}

async function loadDigest(file) {
  STATE.digest = await fetchJSON(`data/${file}`);
  const d = STATE.digest;
  STATE.digestDate = d.report_date;
  $("#freshnessLabel").textContent = `Updated ${(d.generated_at || "").slice(11, 16)} UTC`;
  
  populateTypeFilter(d.incidents);
  populateRegionFilter(d.incidents);
  refreshDateControls();
  // reset filters to a clean view on digest switch
  STATE.filters = { severities: new Set(SEV_ORDER), types: new Set(), regions: new Set(), q: "" };
  STATE.kpiSel = { sev: null, sort: null, type: null };
  STATE.sort = { key: "severity", dir: "asc" };
  $("#searchFilter").value = "";
  renderSevChips();
  renderAll();
}

/* ---------- top-level render ---------- */
function renderAll() {
  renderKPIs();
  renderMap();
  renderTrend();
  renderWatchlist();
  renderDiseaseGrid();
  renderRecentActivity();
}

/* ---------- filters ---------- */
function getFiltered() {
  const f = STATE.filters;
  const q = f.q.trim().toLowerCase();
  return STATE.digest.incidents.filter((i) => {
    if (!f.severities.has(i.severity)) return false;
    if (f.types.size && !f.types.has(i.incident_type)) return false;
    if (f.regions.size && !f.regions.has(i.region)) return false;
    if (q) {
      const hay = [i.canonical_name, i.country, i.disease_name, i.incident_id,
        ...(i.search_keys || []), ...(i.news || []).map((n) => n.headline)]
        .filter(Boolean).join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function populateTypeFilter(incs) {
  STATE._typeKeys = [...new Set(incs.map((i) => i.incident_type))].sort();
  renderTypeChips();
}
function populateRegionFilter(incs) {
  STATE._regionKeys = [...new Set(incs.map((i) => i.region).filter(Boolean))].sort();
  renderRegionChips();
}
function renderTypeChips() {
  const keys = STATE._typeKeys || [];
  const set = STATE.filters.types;
  $("#typeChips").innerHTML = keys.map((t) =>
    `<button class="chip chip--type" type="button" data-val="${esc(t)}" data-on="${set.has(t)}"
       style="--chip-accent:${typeColor(t)}">${esc(t)}</button>`
  ).join("");
}
function renderRegionChips() {
  const keys = STATE._regionKeys || [];
  const set = STATE.filters.regions;
  $("#regionChips").innerHTML = keys.map((r) =>
    `<button class="chip chip--region" type="button" data-val="${esc(r)}" data-on="${set.has(r)}">${esc(r)}</button>`
  ).join("");
}
function populateTrendWindow() {
  const wins = (STATE.aggIndex && STATE.aggIndex.windows) || ["30"];
  $("#trendWindow").innerHTML = wins.map((w) => `<option value="${w}">${w} days</option>`).join("");
  $("#trendWindow").value = STATE.trend.window;
}
function updateTrendSegs() {
  $$(".seg__btn[data-tmetric]").forEach((b) => b.classList.toggle("is-active", b.dataset.tmetric === STATE.trend.metric));
}

function renderSevChips() {
  const f = STATE.filters;
  $("#sevChips").innerHTML = SEV_ORDER.map((s) =>
    `<button class="sevchip" type="button" data-sev="${s}" data-on="${f.severities.has(s)}">${s}</button>`
  ).join("");
}

/* ---------- KPIs (3 axes, 2 tiles each, explicit toggle selection) ---------- */
function renderKPIs() {
  const d = STATE.digest;
  const s = d.summary;
  const k = STATE.kpiSel;
  const asOf = d.as_of || d.report_date;
  const countriesToday = new Set(d.incidents.map((i) => i.country).filter(Boolean)).size;
  const axes = [
    { label: "Severity", tiles: [
      { label: "High+", value: s.critical + s.high, sub: `${s.critical} critical`, cls: "kpi--high", act: "sev:HIGH_PLUS", sel: k.sev === "HIGH_PLUS", hint: "Filter to High + Critical" },
      { label: "Critical", value: s.critical, sub: `${s.high} high`, cls: "kpi--crit", act: "sev:CRITICAL", sel: k.sev === "CRITICAL", hint: "Filter to Critical only" },
    ]},
    { label: "Sort", tiles: [
      { label: "Countries today", value: countriesToday, sub: `${d.incidents.length} incidents`, cls: "kpi--country", act: "sort:event_date:desc", sel: k.sort === "event_date", hint: "Sort by most recent first" },
      { label: "News linked", value: s.news_total, sub: "articles", cls: "kpi--news", act: "sort:news_total:desc", sel: k.sort === "news_total", hint: "Sort by news coverage" },
    ]},
    { label: "Type", tiles: [
      { label: "Active incidents", value: s.reportable_total, sub: `+${s.new_today} today`, cls: "kpi--active", act: "type:ALL", sel: k.type === "ALL", hint: "All types · open watchlist" },
      { label: "Disease outbreaks", value: s.disease_outbreaks, sub: "biological track", cls: "kpi--disease", act: "tab:disease", sel: k.type === "disease", hint: "Open disease pane" },
    ]},
  ];
  $("#kpis").innerHTML = axes.map((ax) => `
    <div class="kpi-axis">
      <h4 class="kpi-axis__label">${ax.label}</h4>
      <div class="kpis kpis--pair">
        ${ax.tiles.map((it) => `
          <div class="kpi ${it.cls} is-action ${it.sel ? "is-selected" : ""}" role="button" tabindex="0"
               aria-pressed="${it.sel}" data-action="${it.act}" title="${esc(it.hint)}">
            <span class="kpi__value">${it.value}</span>
            <span class="kpi__label">${esc(it.label)}</span>
            <span class="kpi__sub">${esc(it.sub)}</span>
          </div>`).join("")}
      </div>
    </div>`).join("");
}

function applyKpiAction(act) {
  const f = STATE.filters;
  const k = STATE.kpiSel;
  const allClear = () => !k.sev && !k.sort && !k.type; // nothing selected in any axis
  let targetTab = null; // null = leave the current tab alone
  if (act === "sev:HIGH_PLUS" || act === "sev:CRITICAL") {
    const target = act === "sev:HIGH_PLUS" ? "HIGH_PLUS" : "CRITICAL";
    const turningOn = k.sev !== target;
    if (turningOn) {
      k.sev = target;
      f.severities = (target === "HIGH_PLUS") ? new Set(["CRITICAL", "HIGH"]) : new Set(["CRITICAL"]);
      showToast(target === "HIGH_PLUS" ? "Filtered to High + Critical" : "Filtered to Critical");
      targetTab = "watchlist";
    } else {
      k.sev = null;
      f.severities = new Set(SEV_ORDER);
      showToast("Severity filter cleared");
      targetTab = allClear() ? "watchlist" : null;
    }
    renderSevChips(); renderAll();
  } else if (act.startsWith("sort:")) {
    const [, key, dir] = act.split(":");
    const tag = key; // "event_date" | "news_total"
    const turningOn = k.sort !== tag;
    if (turningOn) {
      k.sort = tag; STATE.sort = { key, dir: dir || "asc" };
      showToast(tag === "event_date" ? "Sorted by most recent" : "Sorted by news coverage");
      targetTab = "watchlist";
    } else {
      k.sort = null; STATE.sort = { key: "severity", dir: "asc" };
      showToast("Sort reset to severity");
      targetTab = allClear() ? "watchlist" : null;
    }
    renderWatchlist(); renderKPIs();
  } else if (act === "type:ALL") {
    if (k.type === "ALL") { k.type = null; targetTab = allClear() ? "watchlist" : null; }
    else { k.type = "ALL"; f.types = new Set(); renderTypeChips(); renderAll(); showToast("Type filter cleared"); targetTab = "watchlist"; }
    renderKPIs();
  } else if (act.startsWith("tab:")) {
    const name = act.split(":")[1];
    if (k.type === name) { k.type = null; targetTab = allClear() ? "watchlist" : null; }
    else { k.type = name; if (name === "disease") { f.types = new Set(); renderTypeChips(); } renderAll(); targetTab = name; }
    renderKPIs();
  }
  if (targetTab) selectTab(targetTab);
}

function showToast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.hidden = true; }, 2600);
}

/* ---------- MAP (D3) ---------- */
let _world = null, _proj = null, _path = null;
async function ensureWorld() {
  if (_world) return _world;
  _world = await fetchJSON("vendor/world-110m.json");
  return _world;
}
async function renderMap() {
  const svg = d3.select("#worldMap");
  const world = await ensureWorld();
  const countries = topojson.feature(world, world.objects.countries);
  const width = $("#worldMap").clientWidth || 800;
  const height = 420;
  svg.attr("viewBox", `0 0 ${width} ${height}`);

  _proj = d3.geoEqualEarth().fitExtent([[8, 8], [width - 8, height - 8]], countries);
  _path = d3.geoPath(_proj);

  svg.selectAll("*").remove();
  const g = svg.append("g");

  // graticule
  const graticule = d3.geoGraticule().step([20, 20]);
  g.append("path").datum(graticule()).attr("d", _path)
    .attr("fill", "none").attr("stroke", "#ECEEF1").attr("stroke-width", .6);

  g.append("g").attr("class", "countries")
    .selectAll("path").data(countries.features).join("path")
    .attr("class", "country").attr("d", _path);

  // aggregate by country from filtered incidents (size = linked news volume)
  const filtered = getFiltered();
  const byCountry = new Map();
  filtered.forEach((i) => {
    if (i.iso2 === "XX" || i.lat == null) return;
    const c = byCountry.get(i.iso2) || { iso2: i.iso2, country: i.country, count: 0, news: 0, maxRank: 99, lat: i.lat, lon: i.lon };
    c.count += 1;
    c.news += i.news_total || 0;
    c.maxRank = Math.min(c.maxRank, SEV_RANK[i.severity]);
    byCountry.set(i.iso2, c);
  });
  const bubbles = [...byCountry.values()];

  const newsMax = d3.max(bubbles, (d) => d.news) || 1;
  const rScale = d3.scaleSqrt().domain([0, newsMax]).range([4, 24]);

  const bubbleG = g.append("g").attr("class", "bubbles");
  bubbleG.selectAll("circle").data(bubbles).join("circle")
    .attr("class", (d) => "bubble" + (STATE.filters.q && STATE.filters.q.trim().toLowerCase() === d.country.toLowerCase() ? " bubble--sel" : ""))
    .attr("cx", (d) => _proj([d.lon, d.lat])[0])
    .attr("cy", (d) => _proj([d.lon, d.lat])[1])
    .attr("r", (d) => rScale(d.news))
    .attr("fill", (d) => SEV_COLOR[SEV_ORDER[d.maxRank]])
    .attr("fill-opacity", .78)
    .on("click", (e, d) => {
      const cur = STATE.filters.q.trim().toLowerCase();
      STATE.filters.q = (cur === d.country.toLowerCase()) ? "" : d.country;
      $("#searchFilter").value = STATE.filters.q;
      renderAll();
    })
    .append("title").text((d) => `${d.country} · ${d.count} incident(s) · ${d.news} news · max ${SEV_ORDER[d.maxRank]} · click to filter`);

  if (!bubbles.length) {
    g.append("text").attr("x", width / 2).attr("y", height / 2)
      .attr("text-anchor", "middle").style("font-size", "13px").style("fill", "#6E6E6E")
      .text("No incidents match the current filters.");
  }

  // legend
  const legend = $("#mapLegend");
  legend.innerHTML = SEV_ORDER.map((s) =>
    `<span><span class="dot dot--${s}"></span> ${s}</span>`).join("") +
    `<span style="margin-top:4px;color:#6E6E6E">size = news volume</span>`;
}

/* ---------- TREND (multi-line, raw counts on log scale) ---------- */
const METRIC_LABEL = { n: "news", e: "events" };

function buildSeries(data, groupField, keys, colorFn) {
  const metric = STATE.trend.metric;
  const f = STATE.filters;
  return keys.map((k) => ({
    key: k, color: colorFn(k),
    values: data.map((day) => {
      let count = ((day[groupField] || {})[k] || {})[metric] || 0;
      if (count > 0) {
        if (groupField === "type" && f.types.size > 0 && !f.types.has(k)) count = 0;
        if (groupField === "disease" && f.types.size > 0) {
          const incType = diseaseToIncidentType(k);
          if (incType && !f.types.has(incType)) count = 0;
        }
        if (f.severities.size > 0) {
          const sevCount = Object.entries(day.sev || {})
            .filter(([s]) => f.severities.has(s))
            .reduce((sum, [, v]) => sum + (v[metric] || 0), 0);
          const totalSev = Object.values(day.sev || {}).reduce((sum, v) => sum + (v[metric] || 0), 0);
          if (totalSev > 0) count = Math.round(count * sevCount / totalSev);
        }
        if (f.regions.size > 0) {
          const regCount = Object.entries(day.region || {})
            .filter(([r]) => f.regions.has(r))
            .reduce((sum, [, v]) => sum + (v[metric] || 0), 0);
          const totalReg = Object.values(day.region || {}).reduce((sum, v) => sum + (v[metric] || 0), 0);
          if (totalReg > 0) count = Math.round(count * regCount / totalReg);
        }
      }
      return { date: day.date, count };
    }),
  }));
}

function diseaseToIncidentType(disease) {
  if (!disease) return null;
  return "Disease";
}

function renderTrendPanel(svgSel, tooltipSel, tdata, series, bucket) {
  const svg = d3.select(svgSel);
  svg.selectAll("*").remove();
  const t = STATE.trend;
  const perLbl = bucket === "week" ? "wk" : "d";
  const width = (document.querySelector(svgSel).clientWidth) || 520;
  const height = 240, m = { t: 14, r: 16, b: 40, l: 40 };

  const totals = series.map((s) => ({ key: s.key, color: s.color, total: d3.sum(s.values, (v) => v.count), peak: d3.max(s.values, (v) => v.count) || 0 }));
  totals.sort((a, b) => b.total - a.total);
  const globalMax = d3.max(totals, (d) => d.peak) || 1;
  // active series = those with any non-zero value across the window
  const activeSeries = totals.filter((d) => d.total > 0);

  if (!tdata.length || (globalMax <= 1 && activeSeries.length === 0)) {
    svg.attr("viewBox", `0 0 ${width} ${height}`);
    svg.append("text").attr("x", width / 2).attr("y", height / 2).attr("text-anchor", "middle")
      .style("font-size", "13px").style("fill", "#6E6E6E").text("No data for this window.");
    return;
  }

  svg.attr("viewBox", `0 0 ${width} ${height}`);
  const x = d3.scalePoint().domain(tdata.map((d) => d.date)).range([m.l, width - m.r]).padding(0.5);
  const y = d3.scaleSymlog().constant(1).domain([0, globalMax]).range([height - m.b, m.t]);
  const yTicks = [0, 1, 2, 5, 10, 20, 50, 100, 200, 500].filter((v) => v <= globalMax);
  if (globalMax > 0 && !yTicks.includes(globalMax) && globalMax <= 500) yTicks.push(globalMax);

  svg.append("g").selectAll("line").data(yTicks).join("line")
    .attr("x1", m.l).attr("x2", width - m.r)
    .attr("y1", (d) => y(d)).attr("y2", (d) => y(d))
    .attr("stroke", "#ECEEF1");

  svg.append("g").attr("transform", `translate(${m.l},0)`)
    .call(d3.axisLeft(y).tickValues(yTicks).tickFormat((d) => d).tickSize(0))
    .call((g) => g.select(".domain").remove())
    .selectAll("text").classed("trend-axis-label", true);
  svg.append("text").attr("x", m.l).attr("y", m.t - 6)
    .classed("trend-axis-label", true).text(`${METRIC_LABEL[t.metric]} / ${bucket === "week" ? "wk" : "day"}`);

  // active series only — keeps hover tooltip concise
  const seriesByKey = new Map(series.map((s) => [s.key, s]));
  const plotted = activeSeries.map((d) => seriesByKey.get(d.key)).filter(Boolean);

  const line = d3.line().x((d) => x(d.date)).y((d) => y(d.count)).curve(d3.curveMonotoneX);
  plotted.forEach((s) => {
    svg.append("path").datum(s.values).attr("d", line)
      .attr("fill", "none").attr("stroke", s.color)
      .attr("stroke-width", 2).attr("stroke-linejoin", "round").attr("stroke-opacity", .9);
    svg.append("g").selectAll("circle").data(s.values.filter((v) => v.count > 0)).join("circle")
      .attr("cx", (d) => x(d.date)).attr("cy", (d) => y(d.count))
      .attr("r", 2.6).attr("fill", s.color).style("cursor", "pointer")
      .append("title").text((d) => `${fmtDate(d.date)} · ${s.key}: ${d.count} ${METRIC_LABEL[t.metric]}`);
  });

  const step = Math.max(1, Math.ceil(tdata.length / 7));
  svg.append("g").attr("transform", `translate(0,${height - m.b})`)
    .call(d3.axisBottom(x).tickSize(0)
      .tickValues(tdata.map((d) => d.date).filter((_, i) => i % step === 0))
      .tickFormat((d) => (bucket === "week" ? fmtDateYear(d) : fmtDate(d))))
    .call((g) => g.select(".domain").remove())
    .selectAll("text").classed("trend-axis-label", true)
    .attr("transform", "rotate(-30)").style("text-anchor", "end");

  // ---- hover tooltip overlay ----
  const tipEl = document.querySelector(tooltipSel);
  if (!tipEl || !plotted.length) return;
  const dates = tdata.map((d) => d.date);
  // vertical tracker line (hidden until hover)
  const tracker = svg.append("line")
    .attr("class", "trend-tracker")
    .attr("x1", 0).attr("x2", 0)
    .attr("y1", m.t).attr("y2", height - m.b)
    .style("opacity", 0);
  const panelEl = svg.node().closest(".trend-panel");
  const fmtDateLong = (iso) => {
    const dt = new Date(iso + (iso.length === 10 ? "T00:00:00Z" : ""));
    return dt.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
  };
  const renderTip = (iso) => {
    const rows = plotted.map((s) => {
      const v = s.values.find((vv) => vv.date === iso);
      const c = v ? v.count : 0;
      return { key: s.key, color: s.color, count: c };
    }).sort((a, b) => b.count - a.count).map((r) =>
      `<div class="trend-tooltip__row">
        <span class="trend-tooltip__swatch" style="background:${r.color}"></span>
        <span class="trend-tooltip__name">${esc(r.key)}</span>
        <span class="trend-tooltip__value">${r.count}</span>
      </div>`).join("");
    return `<div class="trend-tooltip__date">${fmtDateLong(iso)}</div>${rows}`;
  };
  const showTip = (evt, iso) => {
    tipEl.innerHTML = renderTip(iso);
    tipEl.hidden = false;
    const px = x(iso);
    tracker.attr("x1", px).attr("x2", px).style("opacity", 1);
    // position tooltip near the cursor, clamped to panel
    const panelRect = panelEl.getBoundingClientRect();
    const tipW = tipEl.offsetWidth, tipH = tipEl.offsetHeight;
    let lx = evt.clientX - panelRect.left + 12;
    let ly = evt.clientY - panelRect.top - tipH - 8;
    if (lx + tipW > panelRect.width - 4) lx = evt.clientX - panelRect.left - tipW - 12;
    if (ly < 4) ly = evt.clientY - panelRect.top + 16;
    tipEl.style.left = `${Math.max(4, lx)}px`;
    tipEl.style.top = `${Math.max(4, ly)}px`;
  };
  const hideTip = () => {
    tipEl.hidden = true;
    tracker.style("opacity", 0);
  };
  svg.on("mousemove", function (evt) {
    const rect = svg.node().getBoundingClientRect();
    const px = (evt.clientX - rect.left) * (width / rect.width);
    if (px < m.l || px > width - m.r) { hideTip(); return; }
    // nearest date by x position
    let best = dates[0], bestDist = Infinity;
    for (const d of dates) {
      const dist = Math.abs(x(d) - px);
      if (dist < bestDist) { bestDist = dist; best = d; }
    }
    showTip(evt, best);
  });
  svg.on("mouseleave", hideTip);
}

function renderTrend() {
  const t = STATE.trend;
  const agg = STATE.agg[t.window];
  const data = (agg && agg.series) || [];
  const bucket = (agg && agg.bucket) || "day";

  const geoKeys = [...new Set(data.flatMap((d) => Object.keys(d.type || {})))].sort();
  const disKeys = [...new Set(data.flatMap((d) => Object.keys(d.disease || {})))].sort();
  const geoSeries = buildSeries(data, "type", geoKeys, typeColor);
  const disSeries = buildSeries(data, "disease", disKeys, diseaseColor);

  // shared leading-empty trim so both panels share the same x-range
  const anyActive = (i) =>
    geoSeries.some((s) => s.values[i].count > 0) || disSeries.some((s) => s.values[i].count > 0);
  let firstAct = 0;
  while (firstAct < data.length - 1 && !anyActive(firstAct)) firstAct++;
  const tdata = data.slice(firstAct);
  const tGeo = geoSeries.map((s) => ({ ...s, values: s.values.slice(firstAct) }));
  const tDis = disSeries.map((s) => ({ ...s, values: s.values.slice(firstAct) }));

  renderTrendPanel("#trendGeo", "#trendTipGeo", tdata, tGeo, bucket);
  renderTrendPanel("#trendDisease", "#trendTipDisease", tdata, tDis, bucket);

  const endIso = (agg && agg.as_of) || (tdata.length ? tdata[tdata.length - 1].date : "");
  const startIso = tdata.length ? tdata[0].date : endIso;
  const startLbl = startIso.slice(0, 4) === endIso.slice(0, 4) ? fmtDate(startIso) : fmtDateYear(startIso);
  $("#trendHint").textContent = tdata.length
    ? `${bucket === "week" ? "Weekly" : "Daily"} · ${METRIC_LABEL[t.metric]} · log scale · ${startLbl} → ${fmtDateYear(endIso)}${agg && agg.synthetic ? " · sample data" : ""}`
    : "Aggregation unavailable for this window.";
  $("#trendTitle").textContent = `${t.window}-day trend`;
}

/* ---------- WATCHLIST TABLE ---------- */
const sortableKeys = {
  severity: (i) => SEV_RANK[i.severity],
  priority: (i) => i.priority_rank || 99,
  canonical_name: (i) => i.canonical_name.toLowerCase(),
  country: (i) => (i.country || "").toLowerCase(),
  incident_type: (i) => i.incident_type,
  event_date: (i) => i.event_date,
  news_total: (i) => i.news_total,
  sources: (i) => i.source_count,
  magnitude: (i) => (i.physical && i.physical.max_magnitude != null) ? i.physical.max_magnitude : -Infinity,
};
function renderWatchlist() {
  const tbody = $("#watchTable tbody");
  const rows = sortIncidents(getFiltered());
  $("#cntWatch").textContent = rows.length;
  $("#watchEmpty").hidden = rows.length > 0;
  tbody.innerHTML = rows.map((i) => `
    <tr data-id="${i.incident_id}" class="${i.is_disease ? "is-disease" : ""}">
      <td><span class="chip chip--${i.severity}"><span class="dot dot--${i.severity}"></span>${i.severity}</span></td>
      <td>${i.priority ? `<span class="chip chip--pri${i.priority === 'HIGH' ? 'HIGH' : ''}">${i.priority}</span>` : "—"}</td>
      <td>
        <div class="cell-name">${i.extended_monitoring ? '<span title="Extended monitoring" style="cursor:help">🔁</span> ' : ""}${esc(i.canonical_name)}</div>
        <div class="cell-sub">${i.incident_id}${i.disease_name ? " · " + esc(i.disease_name) : ""}</div>
      </td>
      <td class="cell-country">${esc(i.iso2 === "XX" ? "Global" : i.country)}<small>${esc(i.region || "")}</small></td>
      <td>${typePill(i.incident_type)}</td>
      <td><div class="cell-name">${fmtDate(i.event_date)}</div><div class="cell-sub">${i.days_since_event ?? "?"}d ago</div></td>
      <td class="num"><b>${i.news_total}</b></td>
      <td class="num">${sourceTags(i.sources)}</td>
    </tr>`).join("");
  $$("#watchTable tbody tr").forEach((tr) =>
    tr.addEventListener("click", () => openDrawer(tr.dataset.id)));
}

function sortIncidents(arr) {
  const { key, dir } = STATE.sort;
  const mul = dir === "asc" ? 1 : -1;
  // secondary: news desc, then severity asc
  return [...arr].sort((a, b) => {
    const pa = sortableKeys[key](a), pb = sortableKeys[key](b);
    if (pa < pb) return -1 * mul;
    if (pa > pb) return 1 * mul;
    if (b.news_total !== a.news_total) return b.news_total - a.news_total;
    return SEV_RANK[a.severity] - SEV_RANK[b.severity];
  });
}

/* ---------- DISEASE GRID ---------- */
function renderDiseaseGrid() {
  const items = getFiltered().filter((i) => i.is_disease);
  $("#cntDisease").textContent = items.length;
  $("#diseaseEmpty").hidden = items.length > 0;
  $("#diseaseGrid").innerHTML = items.map((i) => `
    <div class="disease-card" data-id="${i.incident_id}">
      <div class="disease-card__head">
        <div>
          <div class="disease-card__name">${esc(i.disease_name || i.canonical_name)}</div>
          <div class="disease-card__meta">${esc(i.country)} · event ${fmtDate(i.event_date)} · ${i.days_since_event ?? "?"}d ago</div>
        </div>
        <span class="chip chip--${i.severity}">${i.severity}</span>
      </div>
      <div class="disease-card__body">${esc(i.summary || "No summary available.")}</div>
      <div class="disease-card__tags">
        ${i.pandemic_potential && i.pandemic_potential !== "NONE" ? `<span class="tag tag--pp">Pandemic: ${esc(i.pandemic_potential)}</span>` : ""}
        ${i.event_status ? `<span class="tag tag--status">${esc(i.event_status.replace(/_/g, " "))}</span>` : ""}
        ${i.sources.who_don ? `<span class="tag">WHO DON ×${i.sources.who_don}</span>` : ""}
        <span class="tag">${i.news_total} news</span>
      </div>
    </div>`).join("");
  $$(".disease-card").forEach((c) =>
    c.addEventListener("click", () => openDrawer(c.dataset.id)));
}

/* ---------- RECENT ACTIVITY (48h) ---------- */
function renderRecentActivity() {
  // cutoff = digest.as_of - 48h; fall back to latest log/news date if as_of missing
  const asOf = STATE.digest.as_of || STATE.digest.report_date || "";
  const asOfDt = asOf ? new Date(asOf.endsWith("Z") ? asOf : asOf + "T00:00:00Z") : null;
  const cutoff = asOfDt ? new Date(asOfDt.getTime() - 48 * 3600 * 1000) : null;
  const within = (iso) => {
    if (!iso || !cutoff) return false;
    const dt = new Date((iso.length === 10 ? iso + "T00:00:00Z" : iso));
    return dt >= cutoff && dt <= asOfDt;
  };

  // collect events from filtered incidents
  const events = [];
  getFiltered().forEach((inc) => {
    const id = inc.incident_id;
    const name = inc.canonical_name || id;
    const country = inc.iso2 === "XX" ? "Global" : (inc.country || "");
    // new incident: first_reported_date within 48h
    if (within(inc.first_reported_date || inc.event_date)) {
      events.push({
        ts: inc.first_reported_date || inc.event_date,
        kind: "NEW",
        title: "New incident reported",
        detail: name,
        country,
        severity: inc.severity,
        incident_id: id,
      });
    }
    // new logs
    (inc.logs || []).forEach((log) => {
      if (!within(log.log_date)) return;
      events.push({
        ts: log.log_date,
        kind: "LOG",
        title: "New log written",
        detail: (log.summary || "").slice(0, 140),
        incident_name: name,
        country,
        severity: inc.severity,
        incident_id: id,
      });
    });
    // new news (group as one event per incident per day with count)
    const freshNews = (inc.news || []).filter((n) => within(n.published_date));
    if (freshNews.length) {
      // group by date for a concise per-day count
      const byDay = new Map();
      freshNews.forEach((n) => {
        const d = (n.published_date || "").slice(0, 10);
        if (!byDay.has(d)) byDay.set(d, []);
        byDay.get(d).push(n);
      });
      [...byDay.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1)).forEach(([d, items]) => {
        events.push({
          ts: items[0].published_date,
          kind: "NEWS",
          title: `${items.length} new article${items.length === 1 ? "" : "s"}`,
          detail: items[0].headline || name,
          incident_name: name,
          country,
          severity: inc.severity,
          incident_id: id,
        });
      });
    }
  });

  events.sort((a, b) => (b.ts || "").localeCompare(a.ts || ""));

  $("#cntRecent").textContent = events.length;
  $("#recentEmpty").hidden = events.length > 0;

  // summary line
  const newCt = events.filter((e) => e.kind === "NEW").length;
  const logCt = events.filter((e) => e.kind === "LOG").length;
  const newsCt = events.filter((e) => e.kind === "NEWS").length;
  const cutoffLbl = cutoff ? cutoff.toISOString().slice(0, 10) : "—";
  $("#recentSummary").innerHTML = `
    <span><b>${events.length}</b> event(s) in the last 48h (since ${cutoffLbl})</span>
    <span><b>${newCt}</b> new incident(s) · <b>${logCt}</b> new log(s) · <b>${newsCt}</b> news burst(s)</span>
    <span class="news-summary__explain">Newest first · click a row to open the incident · grouped chronologically.</span>`;

  const BADGE = { NEW: "recent-badge--new", LOG: "recent-badge--log", NEWS: "recent-badge--news" };
  const LABEL = { NEW: "NEW", LOG: "LOG", NEWS: "NEWS" };
  $("#recentFeed").innerHTML = events.map((e) => {
    const tsLbl = (e.ts || "").slice(0, 16).replace("T", " ") || "—";
    const name = e.incident_name || e.detail;
    const detailLine = e.kind === "NEW" ? e.detail : e.detail;
    return `
      <div class="recent-row" data-id="${esc(e.incident_id)}">
        <span class="recent-ts">${esc(tsLbl)}</span>
        <span class="recent-badge ${BADGE[e.kind]}">${LABEL[e.kind]}</span>
        <span class="recent-main">
          <div class="recent-name">${esc(name)}</div>
          <div class="recent-detail">${esc(detailLine)}</div>
        </span>
        <span class="recent-meta">
          <span class="dot dot--${e.severity}"></span>${esc(e.severity)} · ${esc(e.country)}
        </span>
      </div>`;
  }).join("");

  $$("#recentFeed .recent-row").forEach((row) =>
    row.addEventListener("click", () => openDrawer(row.dataset.id)));
}

/* ---------- DRAWER ---------- */
function monitoringRequestUrl(i) {
  const repo = "https://github.com/nullhack/src-disaster-awareness";
  const treeId = i.tree_id || i.incident_id;
  const params = new URLSearchParams({
    template: "monitoring_request.yml",
    title: `[Monitoring]: ${treeId.slice(0, 8)} — ${i.canonical_name || ""}`.slice(0, 80),
  });
  params.set("incident-id", treeId);
  return `${repo}/issues/new?${params.toString()}`;
}

function dataBranchUrl(i) {
  const treeId = i.tree_id || i.incident_id;
  return `https://github.com/nullhack/src-disaster-awareness/tree/data/incidents/${treeId}`;
}

function openDrawer(id) {  const i = STATE.digest.incidents.find((x) => x.incident_id === id);
  if (!i) return;
  $("#drawerTitle").textContent = i.canonical_name;
  const phys = i.physical || {};
  const body = `
    <h2>${esc(i.canonical_name)}</h2>
    <div class="drawer__id">
      <code>${i.incident_id}</code>
      <a class="drawer__monitor-link"
         title="Open a GitHub issue to toggle extended monitoring for this incident"
         href="${monitoringRequestUrl(i)}"
         target="_blank" rel="noopener">
        🔁 Flag for extended monitoring
      </a>
      <a class="drawer__data-link"
         title="Browse this incident's files (manifest, reports, news, logs) on the data branch"
         href="${dataBranchUrl(i)}"
         target="_blank" rel="noopener">
        📁 Browse files
      </a>
    </div>
    <div style="display:flex; gap:6px; margin-top:10px; flex-wrap:wrap">
      <span class="chip chip--${i.severity}">${i.severity}</span>
      ${i.priority ? `<span class="chip chip--pri${i.priority === 'HIGH' ? 'HIGH' : ''}">Priority ${i.priority}</span>` : ""}
      <span class="chip chip--pri">${typePill(i.incident_type)}</span>
      ${i.is_disease && i.pandemic_potential && i.pandemic_potential !== "NONE" ? `<span class="tag tag--pp">Pandemic ${esc(i.pandemic_potential)}</span>` : ""}
      ${i.event_status ? `<span class="tag tag--status">${esc(i.event_status.replace(/_/g," "))}</span>` : ""}
      ${i.extended_monitoring ? `<span class="tag" title="Perpetual monitoring regardless of news recency" style="cursor:help">🔁 Extended monitoring</span>` : ""}
    </div>
    ${i.summary ? `<div class="drawer__summary">${esc(i.summary)}</div>` : ""}
    <div class="drawer__section">
      <h3>Key facts</h3>
      <div class="drawer__grid">
        ${kv("Country", `${esc(i.iso2 === "XX" ? "Global" : i.country)} (${i.iso2})`)}
        ${kv("Region", esc(i.region || "—"))}
        ${kv("Country group", esc(i.country_group || "—"))}
        ${kv("Event date", `${fmtDate(i.event_date)} · ${i.days_since_event ?? "?"}d ago`)}
        ${kv("First tracked", fmtDate(i.first_reported_date) || "—")}
        ${kv("Last updated", fmtDate(i.last_updated_date) || "—")}
        ${i.disease_name ? kv("Disease", esc(i.disease_name)) : ""}
        ${phys.max_magnitude != null ? kv("Max magnitude", `M${phys.max_magnitude}`) : ""}
        ${phys.max_depth_km != null ? kv("Depth", `${phys.max_depth_km} km`) : ""}
        ${phys.tsunami ? kv("Tsunami", "⚠ flagged") : ""}
      </div>
    </div>
    ${phys.place ? `<div class="drawer__section"><h3>Locality</h3><div style="font-size:13px;color:#4A4A4A">${esc(phys.place)}</div></div>` : ""}
    <div class="drawer__section">
      <h3>Source coverage · ${i.source_count} record(s)</h3>
      <div class="cell-src">${sourceTagsDetailed(i.sources)}</div>
      ${(i.source_links && i.source_links.length) ? `
        <h4 class="drawer__subhead">Original source records (${i.source_links.length})</h4>
        <ul class="src-links">
          ${i.source_links.map((L) => `
            <li>${L.url ? `<a class="src-link" href="${esc(L.url)}" target="_blank" rel="noopener">` : `<span class="src-link src-link--no-url" aria-disabled="true">`}
              <span class="src-link__type src-link__type--${L.type}">${L.type}</span>
              <span class="src-link__label">${esc(L.label)}${L.meta ? ` <em>${esc(L.meta)}</em>` : ""}</span>
              <span class="src-link__arrow" aria-hidden="true">${L.url ? "↗" : "⊘"}</span>
            ${L.url ? `</a>` : `</span>`}</li>`).join("")}
        </ul>` : `<p class="muted">No deep links available for this incident.</p>`}
    </div>
    ${(i.logs && i.logs.length) ? `<div class="drawer__section"><h3>Timeline · ${i.logs.length} log(s)</h3>
      <ul class="drawer__logs">${i.logs.slice().reverse().map((log, idx) => `
        <li class="log-entry">
          <details>
            <summary>
              <span class="log-entry__head">
                <span class="log-entry__date">${fmtDateTime(log.log_date) || ""}</span>
                <span class="log-entry__count">${log.news.length} article(s)</span>
              </span>
              <div class="log-entry__summary">${esc(log.summary)}</div>
            </summary>
            ${log.news.length ? `<ul class="drawer__news">${log.news.map((n) => `
              <li><a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.headline)}</a>
              <div class="meta">${fmtDate(n.published_date) || ""} · ${esc(n.outlet || "")}</div></li>`).join("")}</ul>` : `<p class="muted">No linked news.</p>`}
          </details>
        </li>`).join("")}</ul></div>` : ""}
    ${(i.news && i.news.length && !(i.logs && i.logs.length)) ? `<div class="drawer__section"><h3>News · ${i.news_total} linked (${i.news.length} shown)</h3>
      <ul class="drawer__news">${i.news.map((n) => `
        <li><a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.headline)}</a>
        <div class="meta">${fmtDate(n.published_date) || ""} · ${esc(n.outlet || "")}</div></li>`).join("")}</ul></div>` : ""}
    ${(i.search_keys && i.search_keys.length) ? `<div class="drawer__section"><h3>Search keys</h3>
      <div class="keys">${i.search_keys.map((k) => `<code>${esc(k)}</code>`).join("")}</div></div>` : ""}
  `;
  $("#drawerBody").innerHTML = body;
  const drawer = $("#drawer");
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
  const scr = $("#scrim"); scr.hidden = false;
  requestAnimationFrame(() => scr.classList.add("show"));
}
function closeDrawer() {
  const drawer = $("#drawer");
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
  const scr = $("#scrim"); scr.classList.remove("show");
  setTimeout(() => { scr.hidden = true; }, 200);
}

/* ---------- helpers ---------- */
function kv(k, v) { return `<div class="drawer__kv"><b>${esc(k)}</b><span>${v}</span></div>`; }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c])); }
function typePill(t) { return `<span style="color:${typeColor(t)};font-weight:600">${esc(t)}</span>`; }
function sourceTags(s) {
  const parts = [];
  if (s.who_don) parts.push(`WHO×${s.who_don}`);
  if (s.usgs) parts.push(`USGS×${s.usgs}`);
  if (s.gdacs) parts.push(`GDACS×${s.gdacs}`);
  if (s.healthmap) parts.push(`HM×${s.healthmap}`);
  return parts.map((p) => `<span class="src-tag">${p}</span>`).join("");
}
function sourceTagsDetailed(s) {
  return [
    s.who_don && `<span class="src-tag">WHO DON ×${s.who_don}</span>`,
    s.usgs && `<span class="src-tag">USGS ×${s.usgs}</span>`,
    s.gdacs && `<span class="src-tag">GDACS ×${s.gdacs}</span>`,
    s.healthmap && `<span class="src-tag">HealthMap ×${s.healthmap}</span>`,
    `<span class="src-tag">News ×${s.news}</span>`,
  ].filter(Boolean).join("");
}
function fmtTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  const HH = String(d.getUTCHours()).padStart(2, "0");
  const MM = String(d.getUTCMinutes()).padStart(2, "0");
  return `${dd}/${mm}/${d.getUTCFullYear()} ${HH}:${MM} UTC`;
}
// All dates render day-first (dd/mm/yyyy) — never US month-first.
function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso.length > 10 ? iso : iso + "T00:00:00Z");
  if (isNaN(d)) return "";
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}/${d.getUTCFullYear()}`;
}
function fmtDateTime(iso) {
  if (!iso) return "";
  if (iso.length <= 10) return fmtDate(iso);
  const d = new Date(iso);
  if (isNaN(d)) return "";
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mi = String(d.getUTCMinutes()).padStart(2, "0");
  return `${dd}/${mm}/${d.getUTCFullYear()} ${hh}:${mi}`;
}
const fmtDateYear = fmtDate;
function showError(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  setTimeout(() => { t.hidden = true; }, 5000);
}

/* ---------- tab switching (shared) ---------- */
function selectTab(name) {
  STATE.tab = name;
  $$(".tab").forEach((x) => x.classList.toggle("tab--active", x.dataset.tab === name));
  $$(".tab-panel").forEach((p) => p.classList.toggle("tab-panel--active", p.dataset.panel === name));
}

/* ---------- event wiring ---------- */
function wireGlobalEvents() {
  renderSevChips();
  $("#sevChips").addEventListener("click", (e) => {
    const b = e.target.closest(".sevchip"); if (!b) return;
    const sev = b.dataset.sev;
    const set = STATE.filters.severities;
    set.has(sev) ? set.delete(sev) : set.add(sev);
    if (set.size === 0) SEV_ORDER.forEach((s) => set.add(s)); // never empty
    STATE.kpiSel.sev = null; renderSevChips(); renderAll();
  });
  $("#typeChips").addEventListener("click", (e) => {
    const b = e.target.closest(".chip"); if (!b) return;
    const v = b.dataset.val, set = STATE.filters.types;
    set.has(v) ? set.delete(v) : set.add(v);
    STATE.kpiSel.type = null; renderTypeChips(); renderAll();
  });
  $("#regionChips").addEventListener("click", (e) => {
    const b = e.target.closest(".chip"); if (!b) return;
    const v = b.dataset.val, set = STATE.filters.regions;
    set.has(v) ? set.delete(v) : set.add(v);
    renderRegionChips(); renderAll();
  });
  $("#searchFilter").addEventListener("input", (e) => { STATE.filters.q = e.target.value; renderAll(); });

  // date picker
  $("#dpPrev").addEventListener("click", () => stepDigest(-1));
  $("#dpNext").addEventListener("click", () => stepDigest(1));
  $("#dpLabel").addEventListener("click", toggleCal);
  $("#dpCal").addEventListener("click", (e) => {
    const nav = e.target.closest("[data-nav]");
    if (nav) {
      const nm = STATE.dpView.m + Number(nav.dataset.nav);
      STATE.dpView = { y: STATE.dpView.y + Math.floor(nm / 12), m: ((nm % 12) + 12) % 12 };
      renderCal();
      return;
    }
    const cell = e.target.closest("[data-date]");
    if (cell) { closeCal(); loadDigestByDate(cell.dataset.date); }
  });
  document.addEventListener("click", (e) => {
    if (!$("#dpCal").hidden && !$("#digestPicker").contains(e.target)) closeCal();
  });

  // trend controls
  $$(".seg__btn[data-tmetric]").forEach((b) => b.addEventListener("click", () => {
    STATE.trend.metric = b.dataset.tmetric; updateTrendSegs(); renderTrend();
  }));
  $("#trendWindow").addEventListener("change", (e) => {
    STATE.trend.window = e.target.value;
    renderTrend();
  });

  // KPI actions (click + keyboard)
  $("#kpis").addEventListener("click", (e) => {
    const k = e.target.closest(".kpi.is-action"); if (!k) return;
    applyKpiAction(k.dataset.action);
  });
  $("#kpis").addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const k = e.target.closest(".kpi.is-action"); if (!k) return;
    e.preventDefault(); applyKpiAction(k.dataset.action);
  });

  $("#clearFilters").addEventListener("click", () => {
    STATE.filters = { severities: new Set(SEV_ORDER), types: new Set(), regions: new Set(), q: "" };
    STATE.kpiSel = { sev: null, sort: null, type: null };
    STATE.sort = { key: "severity", dir: "asc" };
    $("#searchFilter").value = "";
    renderSevChips(); renderTypeChips(); renderRegionChips(); renderAll(); selectTab("watchlist");
  });

  // table sort
  $$("#watchTable thead th").forEach((th) =>
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      if (STATE.sort.key === key) STATE.sort.dir = STATE.sort.dir === "asc" ? "desc" : "asc";
      else { STATE.sort.key = key; STATE.sort.dir = "asc"; }
      STATE.kpiSel.sort = null; renderWatchlist(); renderKPIs();
    }));

  // tabs
  $$(".tab").forEach((t) => t.addEventListener("click", () => { STATE.kpiSel.type = null; selectTab(t.dataset.tab); renderKPIs(); }));

  // drawer close
  $("#drawerClose").addEventListener("click", closeDrawer);
  $("#scrim").addEventListener("click", (e) => { if (e.target === $("#scrim")) closeDrawer(); });
  $("#drawer").addEventListener("click", (e) => e.stopPropagation());
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeCal(); closeDrawer(); } });

  // re-render charts on resize (debounced)
  let rt;
  window.addEventListener("resize", () => {
    clearTimeout(rt);
    rt = setTimeout(() => { renderMap(); renderTrend(); }, 200);
  });
}

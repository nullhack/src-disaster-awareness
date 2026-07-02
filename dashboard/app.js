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
  filters: { severities: new Set(["CRITICAL", "HIGH", "MEDIUM", "LOW"]), type: "", region: "", country: "", q: "" },
  sort: { key: "severity", dir: "asc" },
  tab: "watchlist",
};

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

/* ---------- entry point ---------- */
(async function init() {
  try {
    STATE.manifest = await fetchJSON("data/index.json");
    fillDigestPicker();
    if (!STATE.manifest.digests.length) throw new Error("No digests available.");
    const latest = STATE.manifest.digests[STATE.manifest.digests.length - 1];
    await loadDigest(latest.file);
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
  const sel = $("#digestSelect");
  sel.innerHTML = STATE.manifest.digests
    .map((d) => `<option value="${d.file}">${d.date} · ${d.reportable_total} reportable · ${d.critical} crit</option>`)
    .join("");
  sel.addEventListener("change", async (e) => {
    try { await loadDigest(e.target.value); }
    catch (err) { showError(err.message); }
  });
}

async function loadDigest(file) {
  STATE.digest = await fetchJSON(`data/${file}`);
  const d = STATE.digest;
  $("#freshnessLabel").textContent = `Updated ${fmtTime(d.generated_at)} · ${d.report_date}`;
  $("#schemaVer").textContent = "v" + d.schema_version;
  $("#winDays").textContent = d.tracking_window_days;
  populateTypeFilter(d.incidents);
  populateRegionFilter(d.incidents);
  populateCountryFilter(d.incidents);
  $("#trendTitle").textContent = `${d.tracking_window_days}-day severity trend`;
  renderAll();
}

/* ---------- top-level render ---------- */
function renderAll() {
  renderKPIs();
  renderMap();
  renderTrend();
  renderWatchlist();
  renderDiseaseGrid();
  renderNewsPulse();
}

/* ---------- filters ---------- */
function getFiltered() {
  const f = STATE.filters;
  const q = f.q.trim().toLowerCase();
  return STATE.digest.incidents.filter((i) => {
    if (!f.severities.has(i.severity)) return false;
    if (f.type && i.incident_type !== f.type) return false;
    if (f.region && i.region !== f.region) return false;
    if (f.country && i.country !== f.country) return false;
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
  const types = [...new Set(incs.map((i) => i.incident_type))].sort();
  $("#typeFilter").innerHTML = `<option value="">All types</option>` +
    types.map((t) => `<option>${t}</option>`).join("");
}
function populateRegionFilter(incs) {
  const regions = [...new Set(incs.map((i) => i.region).filter(Boolean))].sort();
  $("#regionFilter").innerHTML = `<option value="">All regions</option>` +
    regions.map((t) => `<option>${t}</option>`).join("");
}
function populateCountryFilter(incs) {
  const countries = [...new Set(incs.map((i) => i.country).filter(Boolean))].sort();
  $("#countryFilter").innerHTML = `<option value="">All countries</option>` +
    countries.map((t) => `<option>${t}</option>`).join("");
}

function renderSevChips() {
  const f = STATE.filters;
  $("#sevChips").innerHTML = SEV_ORDER.map((s) =>
    `<button class="sevchip" type="button" data-sev="${s}" data-on="${f.severities.has(s)}">${s}</button>`
  ).join("");
}

/* ---------- KPIs ---------- */
function renderKPIs() {
  const s = STATE.digest.summary;
  const items = [
    { label: "Reportable", value: s.reportable_total, sub: `+${s.new_today} new today`, cls: "", act: "reset", hint: "Reset filters" },
    { label: "Critical", value: s.critical, sub: `${s.high} high`, cls: "kpi--crit", act: "sev:CRITICAL", hint: "Show critical only" },
    { label: "Disease outbreaks", value: s.disease_outbreaks, sub: "biological track", cls: "kpi--disease", act: "tab:disease", hint: "Open disease pane" },
    { label: "Countries", value: s.countries_affected, sub: "affected", cls: "kpi--country", act: "scroll:.card--map", hint: "Jump to map" },
    { label: "News linked", value: s.news_total, sub: "articles", cls: "kpi--news", act: "tab:news", hint: "Open news pulse" },
    { label: "Max magnitude", value: s.max_magnitude != null ? s.max_magnitude.toFixed(1) : "—", sub: "USGS instrumental", cls: "kpi--high", act: "maxmag", hint: "Open strongest event" },
  ];
  $("#kpis").innerHTML = items.map((it) => `
    <div class="kpi ${it.cls} is-action" role="button" tabindex="0" data-action="${it.act}">
      <span class="kpi__hint">${esc(it.hint)}</span>
      <span class="kpi__value">${it.value}</span>
      <span class="kpi__label">${esc(it.label)}</span>
      <span class="kpi__sub">${esc(it.sub)}</span>
    </div>`).join("");
}

function applyKpiAction(act) {
  if (act === "reset") {
    STATE.filters = { severities: new Set(SEV_ORDER), type: "", region: "", country: "", q: "" };
    $("#typeFilter").value = ""; $("#regionFilter").value = ""; $("#countryFilter").value = ""; $("#searchFilter").value = "";
    renderSevChips();
  } else if (act.startsWith("sev:")) {
    const sev = act.split(":")[1];
    STATE.filters.severities = new Set([sev]);
    renderSevChips();
  } else if (act.startsWith("tab:")) {
    selectTab(act.split(":")[1]);
  } else if (act.startsWith("scroll:")) {
    const el = $(act.split(":")[1]); if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  } else if (act === "maxmag") {
    const incs = STATE.digest.incidents;
    let best = null;
    incs.forEach((i) => {
      const m = i.physical && i.physical.max_magnitude;
      if (m != null && (!best || m > (best.physical && best.physical.max_magnitude || -Infinity))) best = i;
    });
    if (best) { selectTab("watchlist"); openDrawer(best.incident_id); return; }
  }
  renderAll();
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

  // aggregate by country from filtered incidents
  const filtered = getFiltered();
  const byCountry = new Map();
  filtered.forEach((i) => {
    if (i.iso2 === "XX" || i.lat == null) return;
    const c = byCountry.get(i.iso2) || { iso2: i.iso2, country: i.country, count: 0, maxRank: 99, lat: i.lat, lon: i.lon };
    c.count += 1;
    c.maxRank = Math.min(c.maxRank, SEV_RANK[i.severity]);
    byCountry.set(i.iso2, c);
  });
  const bubbles = [...byCountry.values()];

  const rScale = d3.scaleSqrt().domain([1, d3.max(bubbles, (d) => d.count) || 1]).range([5, 22]);

  const bubbleG = g.append("g").attr("class", "bubbles");
  bubbleG.selectAll("circle").data(bubbles).join("circle")
    .attr("class", (d) => "bubble" + (STATE.filters.country === d.country ? " bubble--sel" : ""))
    .attr("cx", (d) => _proj([d.lon, d.lat])[0])
    .attr("cy", (d) => _proj([d.lon, d.lat])[1])
    .attr("r", (d) => rScale(d.count))
    .attr("fill", (d) => SEV_COLOR[SEV_ORDER[d.maxRank]])
    .attr("fill-opacity", .78)
    .on("click", (e, d) => {
      STATE.filters.country = (STATE.filters.country === d.country) ? "" : d.country;
      $("#countryFilter").value = STATE.filters.country;
      renderAll();
    })
    .append("title").text((d) => `${d.country} · ${d.count} incident(s) · max ${SEV_ORDER[d.maxRank]} · click to filter`);

  if (!bubbles.length) {
    g.append("text").attr("x", width / 2).attr("y", height / 2)
      .attr("text-anchor", "middle").style("font-size", "13px").style("fill", "#6E6E6E")
      .text("No incidents match the current filters.");
  }

  // legend
  const legend = $("#mapLegend");
  legend.innerHTML = SEV_ORDER.map((s) =>
    `<span><span class="dot dot--${s}"></span> ${s}</span>`).join("") +
    `<span style="margin-top:4px;color:#6E6E6E">size = count</span>`;
}

/* ---------- TREND (multi-line, % of period peak) ---------- */
function buildTrendSeries() {
  const digest = STATE.digest;
  const win = digest.tracking_window_days || 14;
  const asOf = digest.as_of || digest.report_date;
  const start = new Date(asOf + "T00:00:00Z");
  start.setUTCDate(start.getUTCDate() - (win - 1));
  const dates = [];
  for (let i = 0; i < win; i++) {
    const d = new Date(start);
    d.setUTCDate(start.getUTCDate() + i);
    dates.push(d.toISOString().slice(0, 10));
  }
  const byDate = new Map((digest.trend || []).map((d) => [d.date, d]));
  const series = SEV_ORDER.map((sev) => ({
    sev,
    values: dates.map((dt) => {
      const row = byDate.get(dt) || {};
      return { date: dt, sev, count: row[sev] || 0 };
    }),
  }));
  return { dates, series };
}

function renderTrend() {
  const svg = d3.select("#trendChart");
  svg.selectAll("*").remove();
  const { dates, series } = buildTrendSeries();
  const globalMax = d3.max(series.flatMap((s) => s.values), (v) => v.count) || 1;

  // legend (color index)
  $("#trendLegend").innerHTML = series.map((s) => {
    const peak = d3.max(s.values, (v) => v.count) || 0;
    return `<span class="trend-legend__item">
      <span class="trend-legend__swatch" style="background:${SEV_COLOR[s.sev]}"></span>
      ${s.sev} <span style="color:#6E6E6E;font-weight:500">(peak ${peak}/day)</span>
    </span>`;
  }).join("");

  const width = $("#trendChart").clientWidth || 600;
  const height = 260, m = { t: 16, r: 18, b: 44, l: 40 };
  svg.attr("viewBox", `0 0 ${width} ${height}`);

  const x = d3.scalePoint().domain(dates).range([m.l, width - m.r]).padding(0.5);
  const y = d3.scaleLinear().domain([0, 100]).range([height - m.b, m.t]);
  const pct = (c) => y(globalMax ? (c / globalMax * 100) : 0);

  // gridlines
  svg.append("g").selectAll("line").data([0, 25, 50, 75, 100]).join("line")
    .attr("x1", m.l).attr("x2", width - m.r)
    .attr("y1", (d) => y(d)).attr("y2", (d) => y(d))
    .attr("stroke", "#ECEEF1");

  // y axis (percent)
  svg.append("g").attr("transform", `translate(${m.l},0)`)
    .call(d3.axisLeft(y).tickValues([0, 25, 50, 75, 100]).tickFormat((d) => d + "%").tickSize(0))
    .call((g) => g.select(".domain").remove())
    .selectAll("text").classed("trend-axis-label", true);
  svg.append("text").attr("x", m.l).attr("y", m.t - 6)
    .classed("trend-axis-label", true).text("% of peak day");

  const line = d3.line()
    .x((d) => x(d.date))
    .y((d) => pct(d.count))
    .curve(d3.curveMonotoneX);

  series.forEach((s) => {
    svg.append("path").datum(s.values).attr("d", line)
      .attr("fill", "none").attr("stroke", SEV_COLOR[s.sev])
      .attr("stroke-width", 2).attr("stroke-linejoin", "round");
    svg.append("g").selectAll("circle").data(s.values).join("circle")
      .attr("cx", (d) => x(d.date)).attr("cy", (d) => pct(d.count))
      .attr("r", 2.6).attr("fill", SEV_COLOR[s.sev])
      .style("cursor", "pointer")
      .append("title")
      .text((d) => `${fmtDate(d.date)} · ${s.sev}: ${d.count} incident(s)`);
  });

  // x axis — thin labels to avoid overlap
  const step = Math.max(1, Math.ceil(dates.length / 7));
  const xAxis = d3.axisBottom(x).tickSize(0)
    .tickValues(dates.filter((_, i) => i % step === 0))
    .tickFormat((d) => fmtDate(d));
  svg.append("g").attr("transform", `translate(0,${height - m.b})`)
    .call(xAxis).call((g) => g.select(".domain").remove())
    .selectAll("text").classed("trend-axis-label", true)
    .attr("transform", "rotate(-30)").style("text-anchor", "end");
}

/* ---------- WATCHLIST TABLE ---------- */
const sortableKeys = {
  severity: (i) => SEV_RANK[i.severity],
  priority: (i) => i.priority_rank || 99,
  canonical_name: (i) => i.canonical_name.toLowerCase(),
  country: (i) => i.country.toLowerCase(),
  incident_type: (i) => i.incident_type,
  event_date: (i) => i.event_date,
  news_total: (i) => i.news_total,
  sources: (i) => i.source_count,
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
        <div class="cell-name">${esc(i.canonical_name)}</div>
        <div class="cell-sub">${i.incident_id}${i.disease_name ? " · " + esc(i.disease_name) : ""}</div>
      </td>
      <td class="cell-country">${esc(i.country)}<small>${esc(i.region || "")}</small></td>
      <td>${typePill(i.incident_type)}</td>
      <td><div class="cell-name">${i.event_date}</div><div class="cell-sub">${i.days_since_event ?? "?"}d ago</div></td>
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
          <div class="disease-card__meta">${esc(i.country)} · event ${i.event_date} · ${i.days_since_event ?? "?"}d ago</div>
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

/* ---------- NEWS PULSE ---------- */
function renderNewsPulse() {
  const items = getFiltered().flatMap((i) =>
    (i.news || []).map((n) => ({ ...n, incident: i })));
  items.sort((a, b) => (b.published_date || "").localeCompare(a.published_date || ""));

  // total across the WHOLE digest (before filters) so users see the cap leak honestly
  const totalDigest = STATE.digest.summary.news_total || 0;
  const outlets = [...new Set(items.map((n) => n.outlet).filter(Boolean))];
  const dates = items.map((n) => n.published_date).filter(Boolean).sort();
  const range = dates.length ? `${fmtDate(dates[0])} → ${fmtDate(dates[dates.length - 1])}` : "—";
  const cap = 200;
  const shown = items.slice(0, cap);

  $("#cntNews").textContent = items.length;
  $("#newsEmpty").hidden = items.length > 0;
  $("#newsSummary").innerHTML = `
    <span><b>${items.length}</b> article(s) linked to the filtered incidents</span>
    <span><b>${outlets.length}</b> outlet(s)</span>
    <span>published: <b>${range}</b></span>
    <span>showing <b>${Math.min(shown.length, items.length)}</b> of <b>${items.length}</b>${totalDigest ? ` (digest total ${totalDigest})` : ""}</span>
    <span class="news-summary__explain">Newest first · sorted by publish date · click any row to open the linked incident in the detail drawer.</span>`;
  $("#newsPulse").innerHTML = shown.map((n) => `
    <li data-id="${n.incident.incident_id}">
      <span class="news-date">${esc(n.published_date || "—")}</span>
      <span>
        <div class="news-headline"><a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.headline)}</a></div>
        <div class="news-outlet">${esc(n.outlet || "")} · ${esc(n.incident.country)} · <code>${esc(n.incident.incident_id)}</code></div>
      </span>
      <span class="news-sev"><span class="dot dot--${n.incident.severity}"></span>${n.incident.severity}</span>
    </li>`).join("");
  $$("#newsPulse li").forEach((li) =>
    li.addEventListener("click", (e) => { if (e.target.tagName !== "A") openDrawer(li.dataset.id); }));
}

/* ---------- DRAWER ---------- */
function openDrawer(id) {
  const i = STATE.digest.incidents.find((x) => x.incident_id === id);
  if (!i) return;
  $("#drawerTitle").textContent = i.canonical_name;
  const phys = i.physical || {};
  const body = `
    <h2>${esc(i.canonical_name)}</h2>
    <div class="drawer__id"><code>${i.incident_id}</code></div>
    <div style="display:flex; gap:6px; margin-top:10px; flex-wrap:wrap">
      <span class="chip chip--${i.severity}">${i.severity}</span>
      ${i.priority ? `<span class="chip chip--pri${i.priority === 'HIGH' ? 'HIGH' : ''}">Priority ${i.priority}</span>` : ""}
      <span class="chip chip--pri">${typePill(i.incident_type)}</span>
      ${i.is_disease && i.pandemic_potential && i.pandemic_potential !== "NONE" ? `<span class="tag tag--pp">Pandemic ${esc(i.pandemic_potential)}</span>` : ""}
      ${i.event_status ? `<span class="tag tag--status">${esc(i.event_status.replace(/_/g," "))}</span>` : ""}
    </div>
    ${i.summary ? `<div class="drawer__summary">${esc(i.summary)}</div>` : ""}
    <div class="drawer__section">
      <h3>Key facts</h3>
      <div class="drawer__grid">
        ${kv("Country", `${esc(i.country)} (${i.iso2})`)}
        ${kv("Region", esc(i.region || "—"))}
        ${kv("Country group", esc(i.country_group || "—"))}
        ${kv("Event date", `${esc(i.event_date)} · ${i.days_since_event ?? "?"}d ago`)}
        ${kv("First tracked", esc(i.first_reported_date || "—"))}
        ${kv("Last updated", esc(i.last_updated_date || "—"))}
        ${i.disease_name ? kv("Disease", esc(i.disease_name)) : ""}
        ${phys.max_magnitude != null ? kv("Max magnitude", `M${phys.max_magnitude}`) : ""}
        ${phys.max_depth_km != null ? kv("Depth", `${phys.max_depth_km} km`) : ""}
        ${phys.tsunami ? kv("Tsunami", "⚠ flagged") : ""}
      </div>
    </div>
    ${phys.place ? `<div class="drawer__section"><h3>Locality</h3><div style="font-size:13px;color:#4A4A4A">${esc(phys.place)}</div></div>` : ""}
    <div class="drawer__section">
      <h3>Source coverage · ${i.source_count} record(s)</h3>
      <div class="cell-src">
        ${sourceTagsDetailed(i.sources)}
      </div>
    </div>
    ${(i.news && i.news.length) ? `<div class="drawer__section"><h3>News · ${i.news_total} linked (${i.news.length} shown)</h3>
      <ul class="drawer__news">${i.news.map((n) => `
        <li><a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.headline)}</a>
        <div class="meta">${esc(n.published_date || "")} · ${esc(n.outlet || "")}</div></li>`).join("")}</ul></div>` : ""}
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
  return d.toLocaleString("en-GB", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "UTC" }) + " UTC";
}
function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-GB", { month: "short", day: "numeric", timeZone: "UTC" });
}
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
    renderSevChips(); renderAll();
  });
  $("#typeFilter").addEventListener("change", (e) => { STATE.filters.type = e.target.value; renderAll(); });
  $("#regionFilter").addEventListener("change", (e) => { STATE.filters.region = e.target.value; renderAll(); });
  $("#countryFilter").addEventListener("change", (e) => { STATE.filters.country = e.target.value; renderAll(); });
  $("#searchFilter").addEventListener("input", (e) => { STATE.filters.q = e.target.value; renderAll(); });

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
    STATE.filters = { severities: new Set(SEV_ORDER), type: "", region: "", country: "", q: "" };
    $("#typeFilter").value = ""; $("#regionFilter").value = ""; $("#countryFilter").value = ""; $("#searchFilter").value = "";
    renderSevChips(); renderAll();
  });

  // table sort
  $$("#watchTable thead th").forEach((th) =>
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      if (STATE.sort.key === key) STATE.sort.dir = STATE.sort.dir === "asc" ? "desc" : "asc";
      else { STATE.sort.key = key; STATE.sort.dir = "asc"; }
      renderWatchlist();
    }));

  // tabs
  $$(".tab").forEach((t) => t.addEventListener("click", () => selectTab(t.dataset.tab)));

  // drawer close
  $("#drawerClose").addEventListener("click", closeDrawer);
  $("#scrim").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

  // re-render charts on resize (debounced)
  let rt;
  window.addEventListener("resize", () => {
    clearTimeout(rt);
    rt = setTimeout(() => { renderMap(); renderTrend(); }, 200);
  });
}

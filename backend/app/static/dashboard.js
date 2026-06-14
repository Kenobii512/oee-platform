"use strict";

const COLORS = {
  base: "#39424e", loss: "#f85149", lossSoft: "#d29922",
  oee: "#4ea1ff", visible: "#3fb950", inferred: "#b07cff",
};
const charts = {};
const pct = (x) => (x * 100).toFixed(1) + "%";

function qs() {
  const f = document.getElementById("from").value;
  const t = document.getElementById("to").value;
  const p = new URLSearchParams();
  if (f) p.set("from", f.replace("T", " "));
  if (t) p.set("to", t.replace("T", " "));
  return p.toString() ? "?" + p.toString() : "";
}

async function getJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(path + " -> " + r.status);
  return r.json();
}

function destroy(id) { if (charts[id]) { charts[id].destroy(); delete charts[id]; } }

function renderKpis(oee, dq) {
  document.getElementById("kpi-oee").textContent = pct(oee.oee);
  document.getElementById("kpi-a").textContent = pct(oee.availability);
  document.getElementById("kpi-p").textContent = pct(oee.performance);
  document.getElementById("kpi-q").textContent = pct(oee.quality);
  document.getElementById("kpi-dq").textContent =
    "Duruş " + pct(dq.downtime_entry_coverage) + " · Mikro " + pct(dq.microstop_entry_coverage);
  document.getElementById("dq-detail").innerHTML =
    "Operatör neden-giriş kapsamı:<br>" +
    "• DOWNTIME: <strong>" + pct(dq.downtime_entry_coverage) + "</strong><br>" +
    "• MICROSTOP: <strong>" + pct(dq.microstop_entry_coverage) + "</strong> " +
    "<span class='muted'>(mikro duruşta düşük olması beklenir — içgörü, kusur değil)</span>";
}

function renderWaterfall(oee) {
  const A = oee.availability, P = oee.performance, Q = oee.quality;
  const a100 = A * 100, ap100 = A * P * 100, apq = A * P * Q * 100;
  destroy("waterfall");
  charts.waterfall = new Chart(document.getElementById("waterfall"), {
    type: "bar",
    data: {
      labels: ["Başlangıç", "−Kullanılabilirlik", "−Performans", "−Kalite", "OEE"],
      datasets: [{
        data: [[0, 100], [a100, 100], [ap100, a100], [apq, ap100], [0, apq]],
        backgroundColor: [COLORS.base, COLORS.loss, COLORS.loss, COLORS.loss, COLORS.oee],
      }],
    },
    options: {
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: (c) => {
          const v = c.raw; return (Math.abs(v[1] - v[0])).toFixed(1) + "%"; } } } },
      scales: { y: { min: 0, max: 100, ticks: { color: "#93a1b1" } },
                x: { ticks: { color: "#93a1b1" } } },
    },
  });
}

function lossChart(id, cats) {
  destroy(id);
  charts[id] = new Chart(document.getElementById(id), {
    type: "bar",
    data: {
      labels: cats.map((c) => c.category + (c.kind === "inferred" ? " (çıkarım)" : "")),
      datasets: [{
        data: cats.map((c) => c.value),
        backgroundColor: cats.map((c) => c.kind === "inferred" ? COLORS.inferred : COLORS.visible),
      }],
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: "#93a1b1" } }, y: { ticks: { color: "#93a1b1" } } },
    },
  });
}

function renderLossTree(tree) {
  const cats = tree.categories;
  const timeCats = cats.filter((c) => c.axis === "minutes");
  const partCats = cats.filter((c) => c.axis === "parts");
  lossChart("loss-time", timeCats);
  lossChart("loss-parts", partCats);
}

function renderTrend(series) {
  destroy("trend");
  charts.trend = new Chart(document.getElementById("trend"), {
    type: "line",
    data: {
      labels: series.map((s) => s.period),
      datasets: [
        { label: "OEE", data: series.map((s) => s.oee * 100), borderColor: COLORS.oee, tension: 0.2 },
        { label: "Kullanılabilirlik", data: series.map((s) => s.availability * 100), borderColor: COLORS.visible, tension: 0.2 },
      ],
    },
    options: {
      plugins: { legend: { labels: { color: "#93a1b1" } } },
      scales: { y: { min: 0, max: 100, ticks: { color: "#93a1b1" } },
                x: { ticks: { color: "#93a1b1" } } },
    },
  });
}

function isEmpty(oee) {
  return !oee || (oee.availability === 0 && oee.performance === 0 && oee.quality === 0);
}

async function load() {
  const q = qs();
  let oee;
  try { oee = await getJSON("/oee" + q); } catch (e) { oee = null; }
  const empty = isEmpty(oee);
  document.getElementById("empty-state").classList.toggle("hidden", !empty);
  document.getElementById("dashboard").classList.toggle("hidden", empty);
  if (empty) return;

  const [tree, trend, dq] = await Promise.all([
    getJSON("/loss-tree" + q),
    getJSON("/oee/trend?bucket=day" + (q ? "&" + q.slice(1) : "")),
    getJSON("/data-quality/summary"),
  ]);
  renderKpis(oee, dq);
  renderWaterfall(oee);
  renderLossTree(tree);
  renderTrend(trend);
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const supervisor = btn.dataset.view === "supervisor";
      document.querySelectorAll('[data-role="period"]').forEach((el) =>
        el.classList.toggle("hidden", supervisor));
    });
  });
}

document.getElementById("apply").addEventListener("click", load);
setupTabs();
load();

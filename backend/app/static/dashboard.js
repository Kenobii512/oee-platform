"use strict";

const C = {
  ink: "#eef2f6", muted: "#8b94a3", grid: "rgba(255,255,255,0.05)",
  base: "#3a434f", oee: "#6ea8fe", good: "#34d399", inferred: "#a78bfa", loss: "#fb7185",
};

// Chart.js premium varsayılanları
Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif";
Chart.defaults.font.weight = 500;
Chart.defaults.color = C.muted;

const charts = {};
const pct = (x) => (x * 100).toFixed(1) + "%";
const grid = { color: C.grid, drawTicks: false };
const bar = { borderRadius: 6, borderSkipped: false, barPercentage: 0.62, categoryPercentage: 0.7 };

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
        backgroundColor: [C.base, C.loss, C.loss, C.loss, C.oee],
        ...bar,
      }],
    },
    options: {
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: (c) => (Math.abs(c.raw[1] - c.raw[0])).toFixed(1) + "%" } } },
      scales: { y: { min: 0, max: 100, grid, ticks: { callback: (v) => v + "%" } },
                x: { grid: { display: false } } },
    },
  });
}

function lossChart(id, cats) {
  destroy(id);
  charts[id] = new Chart(document.getElementById(id), {
    type: "bar",
    data: {
      labels: cats.map((c) => c.category + (c.kind === "inferred" ? " · çıkarım" : "")),
      datasets: [{
        data: cats.map((c) => c.value),
        backgroundColor: cats.map((c) => c.kind === "inferred" ? C.inferred : C.good),
        ...bar,
      }],
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: { x: { grid, beginAtZero: true }, y: { grid: { display: false } } },
    },
  });
}

function renderLossTree(tree) {
  const cats = tree.categories;
  lossChart("loss-time", cats.filter((c) => c.axis === "minutes"));
  lossChart("loss-parts", cats.filter((c) => c.axis === "parts"));
}

function renderCostPareto(cost) {
  const cats = cost.categories;  // zaten TL azalan sıralı (backend)
  document.getElementById("cost-total").textContent =
    Math.round(cost.total_tl).toLocaleString("tr-TR") + " TL";
  destroy("cost-pareto");
  charts["cost-pareto"] = new Chart(document.getElementById("cost-pareto"), {
    type: "bar",
    data: {
      labels: cats.map((c) => c.category + (c.kind === "inferred" ? " · çıkarım" : "")),
      datasets: [{
        data: cats.map((c) => Math.round(c.tl)),
        backgroundColor: cats.map((c) => c.kind === "inferred" ? C.inferred : C.loss),
        ...bar,
      }],
    },
    options: {
      indexAxis: "y",
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => ctx.raw.toLocaleString("tr-TR") + " TL" } },
      },
      scales: {
        x: { grid, beginAtZero: true, ticks: { callback: (v) => v.toLocaleString("tr-TR") } },
        y: { grid: { display: false } },
      },
    },
  });
}

function renderRecommendations(rec) {
  const recs = rec.recommendations;  // zaten TL azalan sıralı (backend)
  document.getElementById("rec-total").textContent =
    "~" + Math.round(rec.total_estimated_gain_tl).toLocaleString("tr-TR") + " TL";
  const list = document.getElementById("rec-list");
  list.innerHTML = "";
  for (const r of recs) {
    const li = document.createElement("li");
    li.className = "rec" + (r.kind === "inferred" ? " inferred" : "");
    const gain = Math.round(r.estimated_gain_tl).toLocaleString("tr-TR");
    const tl = Math.round(r.tl).toLocaleString("tr-TR");
    li.innerHTML =
      "<div class='rec-head'><span class='rec-title'>" + r.title + "</span>" +
      "<span class='rec-gain'>~" + gain + " TL/dönem</span></div>" +
      "<p class='rec-action'>" + r.action + "</p>" +
      "<p class='muted rec-meta'>Kayıp: <strong>" + tl + " TL</strong>" +
      (r.kind === "inferred" ? " · çıkarım" : "") +
      " · " + r.assumption + "</p>";
    list.appendChild(li);
  }
}

function renderTrend(series) {
  destroy("trend");
  charts.trend = new Chart(document.getElementById("trend"), {
    type: "line",
    data: {
      labels: series.map((s) => s.period),
      datasets: [
        { label: "OEE", data: series.map((s) => s.oee * 100), borderColor: C.oee,
          backgroundColor: "rgba(110,168,254,0.12)", fill: true, tension: 0.35,
          borderWidth: 2.5, pointRadius: 3, pointBackgroundColor: C.oee },
        { label: "Kullanılabilirlik", data: series.map((s) => s.availability * 100),
          borderColor: C.good, tension: 0.35, borderWidth: 2, pointRadius: 2,
          borderDash: [5, 4], pointBackgroundColor: C.good },
      ],
    },
    options: {
      plugins: { legend: { labels: { usePointStyle: true, boxWidth: 8, padding: 16 } } },
      scales: { y: { min: 0, max: 100, grid, ticks: { callback: (v) => v + "%" } },
                x: { grid: { display: false } } },
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

  const [tree, cost, rec, trend, dq] = await Promise.all([
    getJSON("/loss-tree" + q),
    getJSON("/loss-tree/cost" + q),
    getJSON("/recommendations" + q),
    getJSON("/oee/trend?bucket=day" + (q ? "&" + q.slice(1) : "")),
    getJSON("/data-quality/summary"),
  ]);
  renderKpis(oee, dq);
  renderWaterfall(oee);
  renderLossTree(tree);
  renderCostPareto(cost);
  renderRecommendations(rec);
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

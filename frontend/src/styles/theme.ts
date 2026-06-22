// Chart.js paleti ve paylaşılan stil sabitleri (Jinja dashboard.js 'C' objesinden port).
// "The Foundry Gauge" light/kurumsal palet (DESIGN.md ile birebir).
export const C = {
  ink: '#16202b',
  muted: '#58626f',
  grid: 'rgba(22,32,43,0.07)',
  base: '#c3ccd6',
  oee: '#1f5da6', // kurumsal mavi
  good: '#237a5c', // kullanılabilirlik / görünür
  inferred: '#535f8a', // performans / çıkarımsal
  loss: '#a8443a', // kalite / kayıp
} as const

// OEE bileşeni metrik → renk: TEK doğruluk kaynağı. Hem KPI şeridi (legend noktaları)
// hem OEE trend grafiği bunu kullanır → renkler birebir eşleşir.
export const METRIC = {
  oee: C.oee, // mavi
  availability: C.good, // yeşil
  performance: C.inferred, // mor
  quality: C.loss, // mercan (ilk-geçiş kalite)
  finalYield: C.muted, // gri (nihai verim)
} as const

/** Oran (0–1) → "%xx.x" (tr biçimi). */
export const pct = (x: number): string => (x * 100).toFixed(1) + '%'

/** TL tam sayı tr biçimi (binlik ayraç). */
export const tl = (x: number): string => Math.round(x).toLocaleString('tr-TR')

// Chart.js paylaşılan eksen/bar stilleri.
export const gridAxis = { color: C.grid, drawTicks: false }
export const barStyle = {
  borderRadius: 6,
  borderSkipped: false as const,
  barPercentage: 0.62,
  categoryPercentage: 0.7,
}

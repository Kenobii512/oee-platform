// Chart.js paleti ve paylaşılan stil sabitleri (Jinja dashboard.js 'C' objesinden port).
export const C = {
  ink: '#eef2f6',
  muted: '#8b94a3',
  grid: 'rgba(255,255,255,0.05)',
  base: '#3a434f',
  oee: '#6ea8fe',
  good: '#34d399',
  inferred: '#a78bfa',
  loss: '#fb7185',
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

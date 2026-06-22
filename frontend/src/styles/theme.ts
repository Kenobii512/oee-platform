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

// Kayıp/maliyet kategori kodu → Türkçe isim etiketi (TEK doğruluk kaynağı). Backend
// /loss-tree ve /cost yalnız ham kod döndürür; grafiklerde jargon yerine bunu göster.
// 5 kanonik kategori (backend analytics/loss_tree.py ile birebir). Öneri başlıkları FİİL
// ("Duruşları azalt") olduğundan eksen/legend için ayrı İSİM etiketi tutulur.
export const CATEGORY_LABEL: Record<string, string> = {
  DOWNTIME: 'Duruş',
  MICROSTOP: 'Mikro duruş',
  QUALITY_REDO: 'Yeniden işleme',
  FILL_LOSS: 'Eksik doluluk',
  SPEED_LOSS: 'Hız kaybı',
}

/** Kategori kodunu Türkçe etikete çevir; bilinmeyen kodda ham koda düş (güvenli). */
export const catLabel = (code: string): string => CATEGORY_LABEL[code] ?? code

/** Tek ondalıklı Türkçe sayı (ondalık virgül): 60.1 → "60,1". */
export const num1 = (x: number): string =>
  x.toLocaleString('tr-TR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** Oran (0–1) → "60,1%" (Türkçe ondalık virgül). */
export const pct = (x: number): string => num1(x * 100) + '%'

/** TL tam sayı tr biçimi (binlik ayraç). */
export const tl = (x: number): string => Math.round(x).toLocaleString('tr-TR')

/** Tam sayı tr biçimi (binlik ayraç) — para değil, adet/sayım için (yüklenen/iyi/redo). */
export const int = (x: number): string => Math.round(x).toLocaleString('tr-TR')

/** Dakika → "8 sa 0 dk" (gözlem penceresi gibi süreler). */
export const hm = (min: number): string => {
  const m = Math.max(0, Math.round(min))
  return `${Math.floor(m / 60)} sa ${m % 60} dk`
}

// Chart.js paylaşılan eksen/bar stilleri.
export const gridAxis = { color: C.grid, drawTicks: false }
export const barStyle = {
  // Endüstriyel keskin köşe (--r-sharp/2px) — yumuşak 6px değil.
  borderRadius: 2,
  borderSkipped: false as const,
  barPercentage: 0.62,
  categoryPercentage: 0.7,
}

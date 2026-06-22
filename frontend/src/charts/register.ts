// Chart.js bileşen kaydı + premium global tema (tek yerde; tüm grafiklere uygulanır).
// Bir kez import edilir (main.tsx); react-chartjs-2 instance'ları yönetir.
import {
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  Filler,
  Legend,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from 'chart.js'

import { C } from '../styles/theme'

Chart.register(
  CategoryScale,
  LinearScale,
  BarController, // mixed bar+line (Pareto kümülatif) için controller'lar açık kayıt
  LineController,
  BarElement,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
)

// ---- Global tipografi / renk ----
Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif"
Chart.defaults.font.size = 11.5
Chart.defaults.font.weight = 500
Chart.defaults.color = C.muted

// ---- Keskinlik: grafikleri yüksek-DPI supersampling ile çiz ----
// Düşük-DPI (1x) ekranlarda bile çizgi/metin keskin kalsın diye en az 2x buffer.
// (Chart.js varsayılanı ekran DPR'ını kullanır; bunu tabanı 2'ye yükseltiyoruz.)
Chart.defaults.devicePixelRatio = Math.max(2, window.devicePixelRatio || 1)

// ---- Etkileşim: en yakın noktaya göre, eksen boyunca ----
Chart.defaults.interaction.mode = 'index'
Chart.defaults.interaction.intersect = false

// ---- Legend: nokta-stili, ferah ----
Chart.defaults.plugins.legend.labels.usePointStyle = true
Chart.defaults.plugins.legend.labels.pointStyle = 'circle'
Chart.defaults.plugins.legend.labels.boxWidth = 7
Chart.defaults.plugins.legend.labels.boxHeight = 7
Chart.defaults.plugins.legend.labels.padding = 16
Chart.defaults.plugins.legend.labels.color = C.ink

// ---- Tooltip: açık yüzey, hairline kenar, keskin (kurumsal) ----
const t = Chart.defaults.plugins.tooltip
t.backgroundColor = 'rgba(255, 255, 255, 0.97)'
t.borderColor = 'rgba(22, 32, 43, 0.12)'
t.borderWidth = 1
t.titleColor = C.ink
t.bodyColor = C.muted
t.cornerRadius = 6
t.padding = { x: 12, y: 10 }
t.boxPadding = 6
t.usePointStyle = true
t.titleFont = { family: "'Plus Jakarta Sans', system-ui, sans-serif", weight: 700, size: 12 }
t.bodyFont = { family: "'Plus Jakarta Sans', system-ui, sans-serif", size: 12 }

// ---- Ölçek çizgileri: hairline + eksen kenarı yok (temiz instrument görünüm) ----
Chart.defaults.scale.grid.color = 'rgba(22, 32, 43, 0.07)'
Chart.defaults.scale.grid.drawTicks = false
Chart.defaults.scale.ticks.padding = 8
Chart.defaults.scale.ticks.color = '#677080' // faint — etiketler geri planda

// ---- Animasyon: Chart.js varsayılanı korunur; yalnız reduced-motion'da kapatılır (a11y).
// (animation objesini sıfırdan yazmak iç interpolasyon yapısını bozuyor → varsayılana dokunma.)
const reduceMotion =
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
if (reduceMotion) Chart.defaults.animation = false

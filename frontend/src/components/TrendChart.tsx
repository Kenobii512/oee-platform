// renderTrend karşılığı: OEE dolu çizgi + A/P/Q bileşen çizgileri (G4.1 ile P/Q artık
// pencere-doğru değişir) + nihai verim (Perf-UI). y: 0–100%.
import { Line } from 'react-chartjs-2'
import type { ChartData, ChartOptions, Plugin } from 'chart.js'

import type { TrendPoint } from '../api/types'
import { gridAxis, METRIC } from '../styles/theme'
import Card from './Card'

// HEDEF 85: hedef bölgesi bandı (üst) + kesik referans çizgisi + etiket.
const TARGET = 85
const targetBand: Plugin<'line'> = {
  id: 'targetBand',
  beforeDatasetsDraw(chart) {
    const { ctx, chartArea, scales } = chart
    const y = scales.y?.getPixelForValue(TARGET)
    if (y == null) return
    ctx.save()
    ctx.fillStyle = 'rgba(35,122,92,0.05)' // hedef bölgesi (good, çok hafif)
    ctx.fillRect(chartArea.left, chartArea.top, chartArea.right - chartArea.left, y - chartArea.top)
    ctx.strokeStyle = 'rgba(35,122,92,0.5)'
    ctx.lineWidth = 1
    ctx.setLineDash([5, 4])
    ctx.beginPath()
    ctx.moveTo(chartArea.left, y)
    ctx.lineTo(chartArea.right, y)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = '#237a5c'
    ctx.font = "600 10px 'Plus Jakarta Sans', system-ui, sans-serif"
    ctx.textAlign = 'right'
    ctx.fillText('HEDEF 85', chartArea.right - 6, y - 5)
    ctx.restore()
  },
}

export default function TrendChart({ series }: { series: TrendPoint[] }) {
  const data: ChartData<'line'> = {
    labels: series.map((s) => s.period),
    datasets: [
      {
        label: 'OEE',
        data: series.map((s) => s.oee * 100),
        borderColor: METRIC.oee,
        backgroundColor: 'rgba(31,93,166,0.10)',
        fill: true,
        tension: 0.35,
        borderWidth: 2.5,
        pointRadius: 3,
        pointBackgroundColor: METRIC.oee,
      },
      {
        label: 'Kullanılabilirlik',
        data: series.map((s) => s.availability * 100),
        borderColor: METRIC.availability,
        tension: 0.35,
        borderWidth: 2,
        pointRadius: 2,
        borderDash: [5, 4],
        pointBackgroundColor: METRIC.availability,
      },
      {
        label: 'Performans',
        data: series.map((s) => s.performance * 100),
        borderColor: METRIC.performance,
        tension: 0.35,
        borderWidth: 2,
        pointRadius: 2,
        borderDash: [5, 4],
        pointBackgroundColor: METRIC.performance,
      },
      {
        label: 'Kalite (ilk-geçiş)',
        data: series.map((s) => s.quality * 100),
        borderColor: METRIC.quality,
        tension: 0.35,
        borderWidth: 2,
        pointRadius: 2,
        borderDash: [5, 4],
        pointBackgroundColor: METRIC.quality,
      },
      {
        label: 'Nihai verim',
        data: series.map((s) => s.final_yield * 100),
        borderColor: METRIC.finalYield,
        tension: 0.35,
        borderWidth: 1.5,
        pointRadius: 0,
        borderDash: [2, 3],
        pointBackgroundColor: METRIC.finalYield,
      },
    ],
  }

  const options: ChartOptions<'line'> = {
    plugins: { legend: { labels: { usePointStyle: true, boxWidth: 8, padding: 16 } } },
    scales: {
      y: { min: 0, max: 100, grid: gridAxis, ticks: { callback: (v) => v + '%' } },
      x: { grid: { display: false } },
    },
  }

  return (
    <Card eyebrow="OEE Trendi · gün" period className="card-wide">
      <Line data={data} options={options} plugins={[targetBand]} />
    </Card>
  )
}

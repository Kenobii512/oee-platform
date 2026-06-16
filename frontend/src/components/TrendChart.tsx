// renderTrend karşılığı: OEE dolu çizgi + Kullanılabilirlik kesik çizgi (y: 0–100%).
import { Line } from 'react-chartjs-2'
import type { ChartData, ChartOptions } from 'chart.js'

import type { TrendPoint } from '../api/types'
import { C, gridAxis } from '../styles/theme'
import Card from './Card'

export default function TrendChart({ series }: { series: TrendPoint[] }) {
  const data: ChartData<'line'> = {
    labels: series.map((s) => s.period),
    datasets: [
      {
        label: 'OEE',
        data: series.map((s) => s.oee * 100),
        borderColor: C.oee,
        backgroundColor: 'rgba(110,168,254,0.12)',
        fill: true,
        tension: 0.35,
        borderWidth: 2.5,
        pointRadius: 3,
        pointBackgroundColor: C.oee,
      },
      {
        label: 'Kullanılabilirlik',
        data: series.map((s) => s.availability * 100),
        borderColor: C.good,
        tension: 0.35,
        borderWidth: 2,
        pointRadius: 2,
        borderDash: [5, 4],
        pointBackgroundColor: C.good,
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
    <Card eyebrow="OEE Trendi · gün" period>
      <Line data={data} options={options} />
    </Card>
  )
}

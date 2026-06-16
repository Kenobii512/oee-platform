// renderWaterfall karşılığı: Başlangıç → −A → −P → −Q → OEE şelalesi (stacked-aralık bar).
import { Bar } from 'react-chartjs-2'
import type { ChartData, ChartOptions } from 'chart.js'

import type { Oee } from '../api/types'
import { barStyle, C, gridAxis } from '../styles/theme'
import Card from './Card'

export default function WaterfallChart({ oee }: { oee: Oee }) {
  const A = oee.availability
  const P = oee.performance
  const Q = oee.quality
  const a100 = A * 100
  const ap100 = A * P * 100
  const apq = A * P * Q * 100

  const data: ChartData<'bar'> = {
    labels: ['Başlangıç', '−Kullanılabilirlik', '−Performans', '−Kalite', 'OEE'],
    datasets: [
      {
        data: [
          [0, 100],
          [a100, 100],
          [ap100, a100],
          [apq, ap100],
          [0, apq],
        ] as unknown as number[],
        backgroundColor: [C.base, C.loss, C.loss, C.loss, C.oee],
        ...barStyle,
      },
    ],
  }

  const options: ChartOptions<'bar'> = {
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (c) => {
            const r = c.raw as [number, number]
            return Math.abs(r[1] - r[0]).toFixed(1) + '%'
          },
        },
      },
    },
    scales: {
      y: { min: 0, max: 100, grid: gridAxis, ticks: { callback: (v) => v + '%' } },
      x: { grid: { display: false } },
    },
  }

  return (
    <Card eyebrow="OEE Şelalesi">
      <Bar data={data} options={options} />
    </Card>
  )
}

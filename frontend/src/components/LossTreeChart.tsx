// lossChart karşılığı: yatay bar, eksen-filtreli (dakika/parça). inferred=mor, visible=yeşil.
import { Bar } from 'react-chartjs-2'
import type { ChartData, ChartOptions } from 'chart.js'

import type { LossCat } from '../api/types'
import { barStyle, C, gridAxis } from '../styles/theme'
import Card from './Card'

interface Props {
  eyebrow: string
  cats: LossCat[]
}

export default function LossTreeChart({ eyebrow, cats }: Props) {
  const data: ChartData<'bar'> = {
    labels: cats.map((c) => c.category + (c.kind === 'inferred' ? ' · çıkarım' : '')),
    datasets: [
      {
        data: cats.map((c) => c.value),
        backgroundColor: cats.map((c) => (c.kind === 'inferred' ? C.inferred : C.good)),
        ...barStyle,
      },
    ],
  }

  const options: ChartOptions<'bar'> = {
    indexAxis: 'y',
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: gridAxis, beginAtZero: true },
      y: { grid: { display: false } },
    },
  }

  return (
    <Card eyebrow={eyebrow}>
      <Bar data={data} options={options} />
    </Card>
  )
}

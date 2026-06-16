// renderCostPareto karşılığı: TL azalan yatay bar + toplam satırı. inferred=mor, visible=kırmızı.
import { Bar } from 'react-chartjs-2'
import type { ChartData, ChartOptions } from 'chart.js'

import type { CostTree } from '../api/types'
import { barStyle, C, gridAxis, tl } from '../styles/theme'
import Card from './Card'

export default function CostPareto({ cost }: { cost: CostTree }) {
  const cats = cost.categories // zaten TL azalan sıralı (backend)

  const data: ChartData<'bar'> = {
    labels: cats.map((c) => c.category + (c.kind === 'inferred' ? ' · çıkarım' : '')),
    datasets: [
      {
        data: cats.map((c) => Math.round(c.tl)),
        backgroundColor: cats.map((c) => (c.kind === 'inferred' ? C.inferred : C.loss)),
        ...barStyle,
      },
    ],
  }

  const options: ChartOptions<'bar'> = {
    indexAxis: 'y',
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: { label: (ctx) => (ctx.raw as number).toLocaleString('tr-TR') + ' TL' },
      },
    },
    scales: {
      x: {
        grid: gridAxis,
        beginAtZero: true,
        ticks: { callback: (v) => Number(v).toLocaleString('tr-TR') },
      },
      y: { grid: { display: false } },
    },
  }

  return (
    <Card eyebrow="Maliyet Pareto'su (TL)">
      <span className="muted">varsayım: birim maliyetler config/costs.yaml</span>
      <div className="kpi-line">
        <span className="muted">Toplam kayıp:</span>
        <strong>{tl(cost.total_tl)} TL</strong>
      </div>
      <Bar data={data} options={options} height={220} />
    </Card>
  )
}

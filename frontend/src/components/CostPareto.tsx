// Maliyet Pareto'su: dikey TL barları + kümülatif % eğrisi (sağ eksen).
// "Kayıpların %X'i şu birkaç kalemden" — bir bakışta odak noktası. inferred=indigo, visible=kırmızı.
import { Chart } from 'react-chartjs-2'
import type { ChartData, ChartOptions } from 'chart.js'

import type { CostTree } from '../api/types'
import { barStyle, C, tl } from '../styles/theme'
import Card from './Card'

export default function CostPareto({ cost }: { cost: CostTree }) {
  const cats = cost.categories // zaten TL azalan sıralı (backend)
  const total = cats.reduce((s, c) => s + c.tl, 0) || 1
  // Kümülatif % (immutable): her noktaya kadar olan toplam / genel toplam.
  const cumulative = cats.map((_, i) =>
    Math.round((cats.slice(0, i + 1).reduce((s, c) => s + c.tl, 0) / total) * 100),
  )

  const data: ChartData<'bar' | 'line'> = {
    labels: cats.map((c) => c.category + (c.kind === 'inferred' ? ' · çıkarım' : '')),
    datasets: [
      {
        type: 'bar' as const,
        label: 'Kayıp (TL)',
        data: cats.map((c) => Math.round(c.tl)),
        backgroundColor: cats.map((c) => (c.kind === 'inferred' ? C.inferred : C.loss)),
        yAxisID: 'y',
        order: 2,
        ...barStyle,
      },
      {
        type: 'line' as const,
        label: 'Kümülatif %',
        data: cumulative,
        borderColor: C.oee,
        backgroundColor: C.oee,
        yAxisID: 'yPct',
        order: 1,
        tension: 0.3,
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: C.oee,
      },
    ],
  }

  const options: ChartOptions<'bar' | 'line'> = {
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) =>
            ctx.dataset.type === 'line'
              ? `Kümülatif %${ctx.raw as number}`
              : (ctx.raw as number).toLocaleString('tr-TR') + ' TL',
        },
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: false } },
      y: {
        beginAtZero: true,
        ticks: { callback: (v) => Number(v).toLocaleString('tr-TR') },
      },
      yPct: {
        position: 'right',
        beginAtZero: true,
        max: 100,
        grid: { display: false },
        ticks: { callback: (v) => v + '%', stepSize: 25 },
      },
    },
  }

  return (
    <Card eyebrow="Maliyet Pareto'su (TL)">
      <span className="muted">varsayım: birim maliyetler config/costs.yaml</span>
      <div className="kpi-line">
        <span className="muted">Toplam kayıp:</span>
        <strong>{tl(cost.total_tl)} TL</strong>
      </div>
      <Chart type="bar" data={data} options={options} height={220} />
    </Card>
  )
}

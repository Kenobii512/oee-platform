// Maliyet Pareto'su: dikey TL barları + kümülatif % eğrisi (sağ eksen).
// "Kayıpların %X'i şu birkaç kalemden" — bir bakışta odak noktası. inferred=indigo, visible=kırmızı.
import { Chart } from 'react-chartjs-2'
import type { ChartData, ChartOptions, Plugin } from 'chart.js'

import type { CostTree } from '../api/types'
import { barStyle, C, catLabel, tl } from '../styles/theme'
import Card from './Card'
import Info from './Info'

// Klasik 80/20: kümülatif eksende %80 referans çizgisi.
const pareto80: Plugin<'bar' | 'line'> = {
  id: 'pareto80',
  afterDatasetsDraw(chart) {
    const { ctx, chartArea } = chart
    const y = chart.scales.yPct?.getPixelForValue(80)
    if (y == null) return
    ctx.save()
    ctx.strokeStyle = 'rgba(22,32,43,0.28)'
    ctx.lineWidth = 1
    ctx.setLineDash([4, 4])
    ctx.beginPath()
    ctx.moveTo(chartArea.left, y)
    ctx.lineTo(chartArea.right, y)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = '#58626f'
    ctx.font = "600 9px 'Plus Jakarta Sans', system-ui, sans-serif"
    ctx.textAlign = 'left'
    ctx.fillText('%80', chartArea.left + 4, y - 4)
    ctx.restore()
  },
}

export default function CostPareto({ cost }: { cost: CostTree }) {
  const cats = cost.categories // zaten TL azalan sıralı (backend)
  const total = cats.reduce((s, c) => s + c.tl, 0) || 1
  // Kümülatif % (immutable): her noktaya kadar olan toplam / genel toplam.
  const cumulative = cats.map((_, i) =>
    Math.round((cats.slice(0, i + 1).reduce((s, c) => s + c.tl, 0) / total) * 100),
  )

  const data: ChartData<'bar' | 'line'> = {
    labels: cats.map((c) => catLabel(c.category) + (c.kind === 'inferred' ? ' · çıkarımsal' : '')),
    datasets: [
      {
        type: 'bar' as const,
        label: 'Kayıp (₺)',
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
              : (ctx.raw as number).toLocaleString('tr-TR') + ' ₺',
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
    <Card eyebrow="Maliyet Pareto'su (₺)" className="card-wide">
      <span className="muted">
        varsayım: birim maliyetler <Info text="Kaynak: config/costs.yaml" />
      </span>
      <div className="kpi-line">
        <span className="muted">Toplam kayıp:</span>
        <strong>{tl(cost.total_tl)} ₺</strong>
      </div>
      <Chart type="bar" data={data} options={options} plugins={[pareto80]} height={220} />
    </Card>
  )
}

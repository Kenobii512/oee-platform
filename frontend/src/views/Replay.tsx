// G7 canlı replay: EventSource ile /replay/stream'e abone olur; büyüyen snapshot'ları
// canlı gösterir (düşen OEE, biriken TL, canlı TL Pareto). Oynat/Duraklat/Hız kontrolleri.
import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Line } from 'react-chartjs-2'
import type { ChartData, ChartOptions } from 'chart.js'

import { api } from '../api/client'
import type { ReplaySnapshot } from '../api/types'
import Card from '../components/Card'
import CostPareto from '../components/CostPareto'
import { C, gridAxis, pct, tl } from '../styles/theme'

const STEPS = 60
const SPEEDS = [100, 500, 1000]

export default function Replay() {
  const { data: catalog } = useQuery({ queryKey: ['scenarios'], queryFn: api.scenarios })
  const esRef = useRef<EventSource | null>(null)
  const [scenario, setScenario] = useState('breakdown_storm')
  const [speed, setSpeed] = useState(500)
  const [running, setRunning] = useState(false)
  const [done, setDone] = useState(false)
  const [snap, setSnap] = useState<ReplaySnapshot | null>(null)
  const [series, setSeries] = useState<number[]>([])

  function stop() {
    esRef.current?.close()
    esRef.current = null
    setRunning(false)
  }

  function start() {
    stop()
    setSeries([])
    setSnap(null)
    setDone(false)
    const es = new EventSource(
      `/replay/stream?scenario=${scenario}&speed=${speed}&steps=${STEPS}`,
    )
    es.onmessage = (e) => {
      const s = JSON.parse(e.data) as ReplaySnapshot
      setSnap(s)
      setSeries((prev) => [...prev, s.oee.oee * 100])
    }
    es.addEventListener('done', () => {
      setDone(true)
      stop()
    })
    es.onerror = () => stop()
    esRef.current = es
    setRunning(true)
  }

  // Bileşen söküldüğünde akışı kapat.
  useEffect(() => () => stop(), [])

  const progress = Math.round((series.length / STEPS) * 100)

  const lineData: ChartData<'line'> = {
    labels: series.map((_, i) => `${i + 1}`),
    datasets: [
      {
        label: 'OEE',
        data: series,
        borderColor: C.oee,
        backgroundColor: 'rgba(110,168,254,0.12)',
        fill: true,
        tension: 0.3,
        borderWidth: 2.5,
        pointRadius: 0,
      },
    ],
  }
  const lineOpts: ChartOptions<'line'> = {
    animation: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { min: 0, max: 100, grid: gridAxis, ticks: { callback: (v) => v + '%' } },
      x: { grid: { display: false }, ticks: { display: false } },
    },
  }

  return (
    <>
      <div className="aurora" />
      <header className="topbar">
        <div className="brand">
          <span className="eyebrow">Canlı Replay</span>
          <h1>Bir Haftayı İzle</h1>
        </div>
        <div className="controls">
          <label>
            Senaryo
            <select value={scenario} onChange={(e) => setScenario(e.target.value)} disabled={running}>
              {catalog?.scenarios.map((s) => (
                <option key={s.id} value={s.id}>{s.title}</option>
              ))}
            </select>
          </label>
          <label>
            Hız
            <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} disabled={running}>
              {SPEEDS.map((s) => (
                <option key={s} value={s}>×{s}</option>
              ))}
            </select>
          </label>
          <button onClick={running ? stop : start}>
            {running ? 'Duraklat' : done ? 'Tekrar Oynat' : 'Oynat'}
          </button>
        </div>
      </header>

      <main className="grid">
        <section className="shell kpis">
          <div className="core">
            <div className="kpi kpi-oee">
              <span className="label">OEE {done ? '(final)' : running ? '· canlı' : ''}</span>
              <span className="value">{snap ? pct(snap.oee.oee) : '–'}</span>
            </div>
            <div className="kpi">
              <span className="label">Kullanılabilirlik</span>
              <span className="value">{snap ? pct(snap.oee.availability) : '–'}</span>
            </div>
            <div className="kpi">
              <span className="label">Biriken kayıp</span>
              <span className="value">{snap ? tl(snap.cost.total_tl) + ' TL' : '–'}</span>
            </div>
            <div className="kpi">
              <span className="label">Tahmini kazanç</span>
              <span className="value">{snap ? '~' + tl(snap.total_estimated_gain_tl) + ' TL' : '–'}</span>
            </div>
            <div className="kpi">
              <span className="label">İlerleme</span>
              <span className="value small">
                %{progress} · {snap ? snap.event_count : 0} olay {done ? '· tamamlandı' : ''}
              </span>
            </div>
          </div>
        </section>

        <Card eyebrow="OEE · zaman içinde (düşüş)">
          <Line data={lineData} options={lineOpts} />
        </Card>

        {snap ? (
          <CostPareto cost={snap.cost} />
        ) : (
          <Card eyebrow="Maliyet Pareto'su (TL)">
            <p className="muted">Oynat'a basın — kayıplar biriktikçe canlı dolacak.</p>
          </Card>
        )}
      </main>
    </>
  )
}

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
import GridSkeleton from '../components/GridSkeleton'
import ReplayHero from '../components/ReplayHero'
import ScenarioDropdown from '../components/ScenarioDropdown'
import { C, gridAxis } from '../styles/theme'

const STEPS = 60
// QC: 100/500/1000'de tick (0.2s/speed) hesaplama süresinin altında kalıyor,
// üç seçenek gözle ayırt edilemiyordu. 1/2/5 -> 200/100/40ms: fark görünür.
const SPEEDS = [1, 2, 5]

export default function Replay() {
  const { isLoading: catalogLoading } = useQuery({
    queryKey: ['scenarios'],
    queryFn: api.scenarios,
  })
  const esRef = useRef<EventSource | null>(null)
  const [scenario, setScenario] = useState('breakdown_storm')
  const [speed, setSpeed] = useState(1)
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
        backgroundColor: 'rgba(31,93,166,0.10)',
        fill: true,
        tension: 0.3,
        borderWidth: 2.5,
        // Canlı uç işareti: yalnız son (en güncel) noktada belirgin nokta.
        pointRadius: series.map((_, i) => (i === series.length - 1 ? 4 : 0)),
        pointBackgroundColor: C.oee,
        pointBorderColor: '#fff',
        pointBorderWidth: 1.5,
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
      <header className="apphead-controls">
        <div className="controls">
          <ScenarioDropdown onSelect={setScenario} value={scenario} disabled={running} />
          <div className="ctl-group">
            <span className="viewtoggle-cap">Hız</span>
            <div className="seg" role="group" aria-label="Hız">
              {SPEEDS.map((s) => (
                <button
                  key={s}
                  className={speed === s ? 'active' : ''}
                  disabled={running}
                  onClick={() => setSpeed(s)}
                >
                  ×{s}
                </button>
              ))}
            </div>
          </div>
          <button onClick={running ? stop : start}>
            {running ? 'Duraklat' : done ? 'Tekrar Oynat' : 'Oynat'}
          </button>
        </div>
      </header>

      {catalogLoading || (running && !snap) ? (
        <GridSkeleton cards={2} label="Replay yükleniyor" />
      ) : (
      <main className="grid">
        <div className="zone-head">Canlı Durum</div>
        <ReplayHero snap={snap} progress={progress} running={running} done={done} />

        <div className="zone-head">Biriken Kayıplar</div>
        <Card eyebrow="OEE · Zaman İçinde (Düşüş)" className="card-wide">
          <Line data={lineData} options={lineOpts} />
        </Card>

        {snap ? (
          <CostPareto cost={snap.cost} />
        ) : (
          <Card eyebrow="Maliyet Pareto'su (₺)" className="card-wide">
            <p className="muted">Oynat'a basın. Kayıplar biriktikçe canlı dolacak.</p>
          </Card>
        )}
      </main>
      )}
    </>
  )
}

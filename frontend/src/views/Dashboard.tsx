// Pano sayfası: react-query ile 6 sorgu (oee, loss-tree, cost, recommendations, trend, dq).
// Mevcut Jinja load() mantığının karşılığı: empty-state, Müdür/Amir görünümü, senaryo aktivasyonu.
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { api } from '../api/client'
import type { Oee, Range } from '../api/types'
import CostPareto from '../components/CostPareto'
import DataQualityDetail from '../components/DataQualityDetail'
import GaugeHero from '../components/GaugeHero'
import GridSkeleton from '../components/GridSkeleton'
import LossTreeChart from '../components/LossTreeChart'
import Recommendations from '../components/Recommendations'
import TopBar, { type View } from '../components/TopBar'
import TrendChart from '../components/TrendChart'
import WaterfallChart from '../components/WaterfallChart'

function isEmpty(oee?: Oee): boolean {
  return !oee || (oee.availability === 0 && oee.performance === 0 && oee.quality === 0)
}

export default function Dashboard() {
  const qc = useQueryClient()
  const [range, setRange] = useState<Range>({})
  const [view, setView] = useState<View>('manager')

  const oeeQ = useQuery({ queryKey: ['oee', range], queryFn: () => api.oee(range) })
  const empty = isEmpty(oeeQ.data)
  const enabled = !oeeQ.isLoading && !empty

  const lossQ = useQuery({ queryKey: ['loss', range], queryFn: () => api.lossTree(range), enabled })
  const costQ = useQuery({ queryKey: ['cost', range], queryFn: () => api.cost(range), enabled })
  const recQ = useQuery({ queryKey: ['rec', range], queryFn: () => api.recommendations(range), enabled })
  const trendQ = useQuery({ queryKey: ['trend', range], queryFn: () => api.trend(range), enabled })
  const dqQ = useQuery({ queryKey: ['dq'], queryFn: api.dataQuality, enabled })

  async function activateScenario(id: string) {
    await api.activateScenario(id)
    setRange({}) // senaryo değişiminde filtreleri sıfırla
    await qc.invalidateQueries()
  }

  const manager = view === 'manager'

  return (
    <>
      <div className="aurora" />
      <TopBar
        view={view}
        onViewChange={setView}
        onApply={setRange}
        onActivateScenario={activateScenario}
      />

      {oeeQ.isLoading ? (
        <GridSkeleton kpis={5} cards={4} label="Pano yükleniyor" />
      ) : empty ? (
        <div className="empty">
          Veri yüklü değil. Üst bardan bir <strong>senaryo</strong> seçin ya da{' '}
          <code>POST /ingest</code> ile bir CSV klasörü yükleyin.
        </div>
      ) : (
        <main className="grid">
          {oeeQ.data && dqQ.data && (
            <GaugeHero
              oee={oeeQ.data}
              dq={dqQ.data}
              redoParts={
                lossQ.data?.categories.find((c) => c.category === 'QUALITY_REDO')?.value
              }
            />
          )}
          {oeeQ.data && <WaterfallChart oee={oeeQ.data} />}
          {manager && trendQ.data && <TrendChart series={trendQ.data} />}
          {lossQ.data && (
            <LossTreeChart
              eyebrow="Kayıp Ağacı · Zaman (dakika)"
              cats={lossQ.data.categories.filter((c) => c.axis === 'minutes')}
            />
          )}
          {lossQ.data && (
            <LossTreeChart
              eyebrow="Kayıp Ağacı · Malzeme (parça)"
              cats={lossQ.data.categories.filter((c) => c.axis === 'parts')}
            />
          )}
          {costQ.data && <CostPareto cost={costQ.data} />}
          {recQ.data && <Recommendations rec={recQ.data} />}
          {manager && dqQ.data && <DataQualityDetail dq={dqQ.data} />}
        </main>
      )}
    </>
  )
}

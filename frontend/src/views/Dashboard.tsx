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
import Info from '../components/Info'
import LossTreeChart from '../components/LossTreeChart'
import Recommendations from '../components/Recommendations'
import TopBar, { type View } from '../components/TopBar'
import TrendChart from '../components/TrendChart'

function isEmpty(oee?: Oee): boolean {
  return !oee || (oee.availability === 0 && oee.performance === 0 && oee.quality === 0)
}

// H6: highlight anahtarı -> panodaki grafik adı ("neye bak" ipucu).
const HIGHLIGHT_LABEL: Record<string, string> = {
  cost: "Maliyet Pareto'su",
  loss_tree: 'Kayıp Ağacı',
  trend: 'OEE Trendi',
  oee: 'OEE göstergesi',
}

export default function Dashboard() {
  const qc = useQueryClient()
  const [range, setRange] = useState<Range>({})
  const [view, setView] = useState<View>('detay')
  const [activeScenario, setActiveScenario] = useState<string | undefined>()

  const oeeQ = useQuery({ queryKey: ['oee', range], queryFn: () => api.oee(range) })
  const scenQ = useQuery({ queryKey: ['scenarios'], queryFn: api.scenarios })
  const scenario = scenQ.data?.scenarios.find((s) => s.id === activeScenario)
  const empty = isEmpty(oeeQ.data)
  const enabled = !oeeQ.isLoading && !empty

  const lossQ = useQuery({ queryKey: ['loss', range], queryFn: () => api.lossTree(range), enabled })
  const costQ = useQuery({ queryKey: ['cost', range], queryFn: () => api.cost(range), enabled })
  const recQ = useQuery({ queryKey: ['rec', range], queryFn: () => api.recommendations(range), enabled })
  const trendQ = useQuery({ queryKey: ['trend', range], queryFn: () => api.trend(range), enabled })
  const dqQ = useQuery({ queryKey: ['dq'], queryFn: api.dataQuality, enabled })

  async function activateScenario(id: string) {
    await api.activateScenario(id)
    setActiveScenario(id)
    setRange({}) // senaryo değişiminde filtreleri sıfırla
    await qc.invalidateQueries()
  }

  const detay = view === 'detay'

  return (
    <>
      <TopBar
        view={view}
        onViewChange={setView}
        onApply={setRange}
        onActivateScenario={activateScenario}
      />

      {oeeQ.isLoading ? (
        <GridSkeleton cards={4} label="Pano yükleniyor" />
      ) : oeeQ.isError ? (
        <div className="empty error" role="alert">
          <strong>Veri alınamadı.</strong> Sunucuya ulaşılamıyor olabilir
          {oeeQ.error instanceof Error ? ` (${oeeQ.error.message})` : ''}.
          <button className="retry" onClick={() => oeeQ.refetch()}>
            Yeniden dene
          </button>
        </div>
      ) : empty ? (
        <div className="empty">
          Veri yüklü değil. Üst bardan bir <strong>senaryo</strong> seçin ya da veri kaynağını
          bağlayın. <Info text="Teknik: POST /ingest ile bir CSV klasörü yükleyin." />
        </div>
      ) : (
        <main className="grid">
          {scenario?.narrative && (
            <div className="scenario-banner" role="note">
              <span className="sb-tag">Senaryo</span>
              <span className="sb-title">{scenario.title}</span>
              <span className="sb-narr">{scenario.narrative}</span>
              {scenario.highlight && HIGHLIGHT_LABEL[scenario.highlight] && (
                <span className="sb-hl">👁 Neye bak: {HIGHLIGHT_LABEL[scenario.highlight]}</span>
              )}
            </div>
          )}
          <div className="zone-head">Durum</div>
          {oeeQ.data && dqQ.data && (
            <GaugeHero
              oee={oeeQ.data}
              dq={dqQ.data}
              costTotal={costQ.data?.total_tl}
              trend={trendQ.data}
              redoParts={
                lossQ.data?.categories.find((c) => c.category === 'QUALITY_REDO')?.value
              }
            />
          )}
          {detay && trendQ.data && <TrendChart series={trendQ.data} />}

          <div className="zone-head">Kayıplar</div>
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
              legend={false}
            />
          )}
          {costQ.data && <CostPareto cost={costQ.data} />}

          <div className="zone-head">Aksiyon</div>
          {recQ.data && <Recommendations rec={recQ.data} />}

          {detay && dqQ.data && (
            <>
              <div className="zone-head">Veri Güvenilirliği</div>
              <DataQualityDetail dq={dqQ.data} />
            </>
          )}
        </main>
      )}
    </>
  )
}

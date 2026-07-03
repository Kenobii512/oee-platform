// Canlı hat şeridi: tanklar (banyo kapları) + vinç rayı + askı çipleri, SSE sanal
// saatine senkron SVG. rAF yeniden-çizimi YALNIZ bu bileşendedir (Chart.js kartları
// etkilenmez). Foundry Gauge: keskin köşe, hairline, tabular-nums, glow yok.
import { useMemo } from 'react'

import type { ReplayTimeline } from '../api/types'
import {
  CIKIS,
  YUKLEME,
  buildTimeline,
  lineStateAt,
  tsMs,
  type CarrierState,
} from '../replay/replayLine'
import { useVirtualClock } from '../replay/useVirtualClock'
import { reasonLabel } from '../styles/theme'
import Card from './Card'

interface Props {
  timeline: ReplayTimeline | null
  targetTo: string | null // son SSE snapshot'ının `to` damgası
  tickMs: number // snapshot'lar arası gerçek süre (200/speed)
  running: boolean
  error?: boolean // timeline sorgusu düştü — bekleme metniyle karışmasın
}

// SVG geometrisi (viewBox birimleri; 7 tanka göre ölçülü, tank sayısına uyarlanır).
const CAP_W = 78 // uç kapak genişliği
const TANK_W = 118
const TANK_GAP = 12
const H = 176
const RAIL_Y = 26
const VESSEL_Y = 62
const VESSEL_H = 66
const CHIP_W = 40
const CHIP_H = 22

export default function LineStrip({ timeline, targetTo, tickMs, running, error }: Props) {
  const tl = useMemo(() => (timeline ? buildTimeline(timeline) : null), [timeline])
  const clock = useVirtualClock(targetTo ? tsMs(targetTo) : null, tickMs)

  if (error) {
    return (
      <Card eyebrow="Vinç Rayı ve Tanklar" className="card-wide ls-card">
        <p className="muted">
          Hat verisi yüklenemedi — SSE akışı çalışsa da şerit çizilemez. Senaryoyu yeniden
          seçin ya da sayfayı yenileyin.
        </p>
      </Card>
    )
  }

  if (!tl || clock == null) {
    return (
      <Card eyebrow="Vinç Rayı ve Tanklar" className="card-wide ls-card">
        <p className="muted">
          Oynat'a basın — hat canlanacak: askılar tanklarda ilerler, duruşlar kızarır,
          redo askıları geri döner.
        </p>
      </Card>
    )
  }

  const state = lineStateAt(tl, clock)
  const n = state.tanks.length
  const W = CAP_W * 2 + 40 + n * (TANK_W + TANK_GAP)
  const tankX = (i: number) => CAP_W + 20 + i * (TANK_W + TANK_GAP)
  const idxOf = new Map(state.tanks.map((t, i) => [t.id, i]))
  const loadX = CAP_W / 2 + 4
  const exitX = W - CAP_W / 2 - 4
  // İstasyon → çip merkez x'i (pseudo-istasyonlar uç kapaklara düşer).
  // Hat tanımında olmayan istasyon (config sapması/kirli veri) → null: sessizce
  // ilk tanka çizmek yerine hiç çizilmez.
  const cx = (station: string): number | null => {
    if (station === YUKLEME) return loadX
    if (station === CIKIS) return exitX
    const i = idxOf.get(station)
    return i == null ? null : tankX(i) + TANK_W / 2
  }
  const hoistA = state.hoist.from != null ? cx(state.hoist.from) : null
  const hoistB = state.hoist.to != null ? cx(state.hoist.to) : null

  const clockLabel = new Date(clock).toLocaleTimeString('tr-TR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

  const chip = (c: CarrierState) => {
    const p = c.pos
    let x: number
    let y: number
    if (p.kind === 'tankta' || p.kind === 'bekliyor') {
      const sx = cx(p.station)
      if (sx == null) return null
      x = sx
      y = VESSEL_Y + 32
    } else if (p.kind === 'tasiniyor') {
      const a = cx(p.from)
      const b = cx(p.to)
      if (a == null || b == null) return null
      x = a + (b - a) * p.progress
      y = RAIL_Y + 8
    } else if (p.kind === 'strip') {
      // Söküm/geri dönüş: çıkıştan yüklemeye, alttaki kesikli dönüş yolunda.
      x = exitX + (loadX - exitX) * p.progress
      y = H - 14
    } else {
      return null
    }
    const cls = `ls-chip${c.redo ? ' ls-chip-redo' : ''}${p.kind === 'bekliyor' ? ' ls-chip-bekliyor' : ''}`
    return (
      <g key={c.id} className={cls} transform={`translate(${x}, ${y})`}>
        <rect x={-CHIP_W / 2} y={-CHIP_H / 2} width={CHIP_W} height={CHIP_H} rx={2} />
        <text y={4}>{c.id.slice(-4)}</text>
      </g>
    )
  }

  return (
    <Card eyebrow="Vinç Rayı ve Tanklar" className="card-wide ls-card">
      <div className="ls-head">
        <span className="ls-clock" aria-label="Sanal saat">
          {clockLabel}
        </span>
        <div className="ls-counters">
          <span>
            Yüklenen <strong>{state.yuklenen}</strong>
          </span>
          <span>
            Çıkan <strong>{state.cikan}</strong>
          </span>
          <span className="ls-cnt-redo">
            Redo <strong>{state.redo}</strong>
          </span>
        </div>
      </div>
      <div className="ls-scroll">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className={`ls-svg${running ? '' : ' ls-paused'}`}
          role="img"
          aria-label="Canlı hat şeridi"
        >
          {/* Vinç rayı */}
          <line className="ls-rail" x1={loadX} y1={RAIL_Y} x2={exitX} y2={RAIL_Y} />
          {state.hoist.durum === 'durus' && (
            <text className="ls-reason ls-hoist-reason" x={W / 2} y={RAIL_Y - 10}>
              {reasonLabel(state.hoist.reason ?? '')}
            </text>
          )}
          {/* Uç kapaklar */}
          <g className="ls-cap" transform={`translate(4, ${VESSEL_Y})`}>
            <rect width={CAP_W} height={VESSEL_H} />
            <text x={CAP_W / 2} y={VESSEL_H / 2 + 4}>
              Yükleme →
            </text>
          </g>
          <g className="ls-cap" transform={`translate(${W - CAP_W - 4}, ${VESSEL_Y})`}>
            <rect width={CAP_W} height={VESSEL_H} />
            <text x={CAP_W / 2} y={VESSEL_H / 2 + 4}>
              → QC / Çıkış
            </text>
          </g>
          {/* Dönüş yolu (redo) — kesikli */}
          <line className="ls-return" x1={exitX} y1={H - 14} x2={loadX} y2={H - 14} />
          {/* Tanklar */}
          {state.tanks.map((tk, i) => (
            <g key={tk.id} transform={`translate(${tankX(i)}, 0)`}>
              <g
                className={`ls-tank ls-tank-${tk.durum}${tk.durum === 'mikro' ? ' ls-flash' : ''}`}
              >
                <rect className="ls-vessel" x={0} y={VESSEL_Y} width={TANK_W} height={VESSEL_H} />
                <rect
                  className="ls-liquid"
                  x={4}
                  y={VESSEL_Y + 22}
                  width={TANK_W - 8}
                  height={VESSEL_H - 26}
                />
              </g>
              {tk.durum === 'durus' && tk.reason && (
                <text className="ls-reason" x={TANK_W / 2} y={VESSEL_Y - 8}>
                  {reasonLabel(tk.reason)}
                </text>
              )}
              <text className="ls-tankname" x={TANK_W / 2} y={VESSEL_Y + VESSEL_H + 18}>
                {tk.name}
              </text>
            </g>
          ))}
          {/* Vinç troleyi */}
          {state.hoist.durum === 'tasiyor' && hoistA != null && hoistB != null && (
            <rect
              className="ls-trolley"
              x={hoistA + (hoistB - hoistA) * (state.hoist.progress ?? 0) - 10}
              y={RAIL_Y - 5}
              width={20}
              height={10}
            />
          )}
          {state.hoist.durum === 'durus' && (
            <rect className="ls-trolley ls-trolley-durus" x={W / 2 - 10} y={RAIL_Y - 5} width={20} height={10} />
          )}
          {/* Askı çipleri */}
          {state.carriers.map(chip)}
        </svg>
      </div>
    </Card>
  )
}

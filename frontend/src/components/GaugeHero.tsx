// "Control Strip" hero (cesur kurgu): solda OEE gauge çapası, sağda A×P×Q kanal
// kaskadı + her kanalın OEE'ye kattığı kayıp, altta toplam kayıp. Hero + şelale +
// maliyet başlığını tek kararlı banda toplar. Amaçlı motion: gauge dolumu, count-up,
// metre fill (reduced-motion / test ortamında anında final).
import { useEffect, useState } from 'react'

import type { DataQuality, Oee, TrendPoint } from '../api/types'
import { int, METRIC, num1, pct, tl } from '../styles/theme'
import Dial, { TARGET } from './Dial'

/** Küçük OEE sparkline (son N vardiya eğilimi). */
function Spark({ data }: { data: number[] }) {
  if (data.length < 2) return null
  const w = 200
  const h = 30
  const pad = 3
  const min = Math.min(...data)
  const max = Math.max(...data)
  const rng = max - min || 1
  const pts = data.map((val, i) => {
    const x = pad + (i / (data.length - 1)) * (w - 2 * pad)
    const y = pad + (1 - (val - min) / rng) * (h - 2 * pad)
    return [x, y] as const
  })
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ')
  const last = pts[pts.length - 1]
  return (
    <svg className="spark" width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
      <path d={d} fill="none" stroke="#1f5da6" strokeWidth="1.5" strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r="2.5" fill="#1f5da6" />
    </svg>
  )
}

/** Animasyon kapalı mı: SSR/test (matchMedia yok) ya da reduced-motion → anında final. */
function instant(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return true
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** 0 → target easeOutCubic count-up (rAF). Anında modda (test/SSR/reduced) target döner. */
function useCountUp(target: number, ms = 900): number {
  const reduced = instant()
  const [v, setV] = useState(reduced ? target : 0)
  useEffect(() => {
    if (reduced) return // animasyon yok; render doğrudan target döner
    let raf = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms)
      setV(target * (1 - Math.pow(1 - t, 3)))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms, reduced])
  return reduced ? target : v
}

/** Pano gauge: mount'ta 0→değer count-up; paylaşılan Dial'i besler. */
function Gauge({ value }: { value: number }) {
  return <Dial value={useCountUp(value)} />
}

interface ChannelProps {
  label: string
  value: number
  loss: number // OEE'ye kattığı kayıp (puan)
  color: string
  sub?: React.ReactNode
}

function Channel({ label, value, loss, color, sub }: ChannelProps) {
  const v = useCountUp(value)
  return (
    <div className="ctile">
      <span className="ck">
        <span className="sq" style={{ background: color }} />
        {label}
      </span>
      <div className="cv">
        {num1(v * 100)}
        <small>%</small>
      </div>
      <div className="meter">
        <i style={{ transform: `scaleX(${Math.min(1, v)})`, background: color }} />
      </div>
      <div className="closs">−{num1(loss)} puan</div>
      {sub && <div className="csub">{sub}</div>}
    </div>
  )
}

interface Props {
  oee: Oee
  dq: DataQuality
  /** Toplam önlenebilir kayıp (cost endpoint total_tl). */
  costTotal?: number
  /** Redo'dan geçen ayrık parça sayısı (loss-tree QUALITY_REDO). */
  redoParts?: number
  /** OEE trend serisi — gauge altı sparkline (yoksa gizlenir). */
  trend?: TrendPoint[]
}

export default function GaugeHero({ oee, dq, costTotal, redoParts, trend }: Props) {
  const deltaPP = (oee.oee - TARGET) * 100
  const below = deltaPP < 0
  const spark = trend?.map((t) => t.oee) ?? []
  const A = oee.availability
  const P = oee.performance
  const Q = oee.quality
  // Kaskad: her kanalın OEE'ye kattığı puan kaybı (şelale adımları).
  const lossA = (1 - A) * 100
  const lossP = A * (1 - P) * 100
  const lossQ = A * P * (1 - Q) * 100
  const finalYield = oee.final_yield ?? 1
  const redoNote = redoParts != null && redoParts > 0 ? ` · ${Math.round(redoParts)} redo` : ''
  // Kullanılabilirlik bağlamı: planlı vs plansız duruş (her zaman görünür alt-bilgi).
  const hasDown = oee.planned_downtime_min != null || oee.downtime_union_min != null
  const downSub = hasDown ? (
    <>
      Planlı <strong>{int(oee.planned_downtime_min ?? 0)} dk</strong> · Plansız{' '}
      <strong>{int(oee.downtime_union_min ?? 0)} dk</strong>
    </>
  ) : undefined

  return (
    <section className="shell fhero">
      <div className="core">
        <div className="cstrip">
          <div className="cs-gauge">
            <span className="gcap">OEE</span>
            <Gauge value={oee.oee} />
            <div className="gscale">
              <span>0</span>
              <span>HEDEF 85</span>
              <span>100</span>
            </div>
            {spark.length > 1 && <Spark data={spark} />}
            <div className={`gdelta${below ? ' neg' : ' pos'}`}>
              {below ? 'HEDEF ALTINDA' : 'HEDEF ÜSTÜ'} · {below ? '−' : '+'}
              {num1(Math.abs(deltaPP))} p
            </div>
          </div>

          <div className="cs-cascade">
            <div className="cs-channels">
              <Channel
                label="Kullanılabilirlik"
                value={A}
                loss={lossA}
                color={METRIC.availability}
                sub={downSub}
              />
              <span className="cs-arrow" aria-hidden="true">→</span>
              <Channel label="Performans" value={P} loss={lossP} color={METRIC.performance} />
              <span className="cs-arrow" aria-hidden="true">→</span>
              <Channel
                label="Kalite (ilk-geçiş)"
                value={Q}
                loss={lossQ}
                color={METRIC.quality}
                sub={
                  <>
                    Nihai verim <strong>{pct(finalYield)}</strong>
                    {redoNote}
                  </>
                }
              />
            </div>

            <div className="cs-cost">
              <div className="cs-cost-main">
                <span className="cs-cost-k">Toplam kayıp</span>
                <strong>{costTotal != null ? `${tl(costTotal)} ₺` : '—'}</strong>
                <span className="cs-cost-u">/ vardiya</span>
              </div>
              <div className="cs-dq">
                Veri güvenilirliği · mikro-duruş girişi <strong>{pct(dq.microstop_entry_coverage)}</strong>
                <span className="cs-dq-note">tek manuel girdi; gerisi sistemce</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

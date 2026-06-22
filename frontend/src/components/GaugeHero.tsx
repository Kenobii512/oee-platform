// "Control Strip" hero (cesur kurgu): solda OEE gauge çapası, sağda A×P×Q kanal
// kaskadı + her kanalın OEE'ye kattığı kayıp, altta toplam kayıp. Hero + şelale +
// maliyet başlığını tek kararlı banda toplar. Amaçlı motion: gauge dolumu, count-up,
// metre fill (reduced-motion / test ortamında anında final).
import { useEffect, useState } from 'react'

import type { DataQuality, Oee } from '../api/types'
import { METRIC, pct, tl } from '../styles/theme'

const ARC = Math.PI * 84 // yarım daire yay uzunluğu (r=84)
const TARGET = 0.85 // OEE hedefi (gauge HEDEF işareti)

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

function Gauge({ value }: { value: number }) {
  const v = Math.max(0, Math.min(1, useCountUp(value)))
  const offset = ARC * (1 - v)
  const deltaPP = (value - TARGET) * 100
  const below = deltaPP < 0
  return (
    <>
      <div className="dial">
        <svg width="200" height="118" viewBox="0 0 200 118" role="img" aria-label={`OEE ${pct(value)}`}>
          <path d="M16 110 A84 84 0 0 1 184 110" fill="none" stroke="#e7ebf0" strokeWidth="16" strokeLinecap="round" />
          <path d="M16 110 A84 84 0 0 1 184 110" fill="none" stroke="url(#gz)" strokeWidth="4" strokeLinecap="round" opacity="0.7" />
          <path
            d="M16 110 A84 84 0 0 1 184 110"
            fill="none"
            stroke="#1f5da6"
            strokeWidth="16"
            strokeLinecap="round"
            strokeDasharray={ARC}
            strokeDashoffset={offset}
          />
          <defs>
            <linearGradient id="gz" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="#a8443a" />
              <stop offset="0.5" stopColor="#b5832f" />
              <stop offset="1" stopColor="#237a5c" />
            </linearGradient>
          </defs>
        </svg>
        <div className="read">
          <span className="n">{(v * 100).toFixed(1)}</span>
          <span className="u">% OEE</span>
        </div>
      </div>
      <div className="gscale">
        <span>0</span>
        <span>HEDEF 85</span>
        <span>100</span>
      </div>
      <div className={`gdelta${below ? ' neg' : ' pos'}`}>
        {below ? '▼' : '▲'} {Math.abs(deltaPP).toFixed(1)} puan {below ? 'hedefin altında' : 'hedef üstü'}
      </div>
    </>
  )
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
        {(v * 100).toFixed(1)}
        <small>%</small>
      </div>
      <div className="meter">
        <i style={{ transform: `scaleX(${Math.min(1, v)})`, background: color }} />
      </div>
      <div className="closs">−{loss.toFixed(1)} puan</div>
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
}

export default function GaugeHero({ oee, dq, costTotal, redoParts }: Props) {
  const A = oee.availability
  const P = oee.performance
  const Q = oee.quality
  // Kaskad: her kanalın OEE'ye kattığı puan kaybı (şelale adımları).
  const lossA = (1 - A) * 100
  const lossP = A * (1 - P) * 100
  const lossQ = A * P * (1 - Q) * 100
  const finalYield = oee.final_yield ?? 1
  const redoNote = redoParts != null && redoParts > 0 ? ` · ${Math.round(redoParts)} redo` : ''

  return (
    <section className="shell fhero">
      <div className="core">
        <div className="cstrip">
          <div className="cs-gauge">
            <span className="gcap">OEE</span>
            <Gauge value={oee.oee} />
          </div>

          <div className="cs-cascade">
            <div className="cs-channels">
              <Channel label="Kullanılabilirlik" value={A} loss={lossA} color={METRIC.availability} />
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
                <span className="cs-cost-k">Toplam önlenebilir kayıp</span>
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

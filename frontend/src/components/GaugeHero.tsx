// "The Foundry Gauge" imza hero: OEE gauge kadranı + A/P/Q eşikli metre hücreleri.
// KpiCards'ın yerini alır. Gauge dolumu HEP mavi (One Blue Rule); kanallar yeşil/indigo/kırmızı.
import type { DataQuality, Oee } from '../api/types'
import { METRIC, pct } from '../styles/theme'

interface Props {
  oee: Oee
  dq: DataQuality
  /** Redo'dan geçen ayrık parça sayısı (loss-tree QUALITY_REDO) — çift kalite anlatısı. */
  redoParts?: number
}

// Yarım daire yay uzunluğu: π·r (r=84) ≈ 263.9. Dolum offset'i orana göre.
const ARC = Math.PI * 84

function Gauge({ value }: { value: number }) {
  const v = Math.max(0, Math.min(1, value))
  const offset = ARC * (1 - v)
  return (
    <div className="dial">
      <svg width="200" height="118" viewBox="0 0 200 118" role="img" aria-label={`OEE ${pct(v)}`}>
        {/* yatak */}
        <path d="M16 110 A84 84 0 0 1 184 110" fill="none" stroke="#e7ebf0" strokeWidth="16" strokeLinecap="round" />
        {/* hedef bandı: kırmızı→amber→yeşil (referans, dolum değil) */}
        <path d="M16 110 A84 84 0 0 1 184 110" fill="none" stroke="url(#gz)" strokeWidth="4" strokeLinecap="round" opacity="0.7" />
        {/* dolum: hep mavi */}
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
  )
}

interface CellProps {
  label: string
  value: number
  color: string
  sub?: React.ReactNode
}

function MetricCell({ label, value, color, sub }: CellProps) {
  return (
    <div className="mcell">
      <span className="mk">
        <span className="sq" style={{ background: color }} />
        {label}
      </span>
      <div className="mn">
        {(value * 100).toFixed(1)}
        <small>%</small>
      </div>
      <div className="meter">
        <i style={{ width: `${Math.min(100, value * 100)}%`, background: color }} />
      </div>
      {sub && <div className="msub">{sub}</div>}
    </div>
  )
}

export default function GaugeHero({ oee, dq, redoParts }: Props) {
  const finalYield = oee.final_yield ?? 1
  const redoNote = redoParts != null && redoParts > 0 ? ` · ${Math.round(redoParts)} redo` : ''
  return (
    <section className="shell fhero">
      <div className="core">
        <div className="fgrid">
          {/* Gauge paneli */}
          <div className="gpanel">
            <span className="gcap">OEE</span>
            <Gauge value={oee.oee} />
            <div className="gscale">
              <span>0</span>
              <span>HEDEF 85</span>
              <span>100</span>
            </div>
            <div className="gdq">
              Veri güvenilirliği · mikro-duruş girişi <strong>{pct(dq.microstop_entry_coverage)}</strong>
              <br />
              tek manuel girdi; gerisi sistemce
            </div>
          </div>

          {/* Eşikli metre hücreleri */}
          <div className="mgrid">
            <MetricCell label="Kullanılabilirlik" value={oee.availability} color={METRIC.availability} />
            <MetricCell label="Performans" value={oee.performance} color={METRIC.performance} />
            <MetricCell
              label="Kalite (ilk-geçiş)"
              value={oee.quality}
              color={METRIC.quality}
              sub={
                <>
                  Nihai verim <strong>{pct(finalYield)}</strong>
                  {redoNote}
                </>
              }
            />
          </div>
        </div>
      </div>
    </section>
  )
}

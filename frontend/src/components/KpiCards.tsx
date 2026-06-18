// renderKpis karşılığı: OEE/A/P/Q + veri güvenilirliği özeti. .kpis tam genişlik kartı.
// Etiketlerdeki renk noktaları OEE trend grafiğinin seri renkleriyle BİREBİR aynıdır (METRIC).
import type { DataQuality, Oee } from '../api/types'
import { METRIC, pct } from '../styles/theme'

interface Props {
  oee: Oee
  dq: DataQuality
  /** Redo'dan geçen ayrık parça sayısı (loss-tree QUALITY_REDO) — çift kalite anlatısı için. */
  redoParts?: number
}

export default function KpiCards({ oee, dq, redoParts }: Props) {
  // Çift kalite (no-scrap): OEE'nin Q'su ilk-geçiş; nihai verim ayrı (≈%100).
  const finalYield = oee.final_yield ?? 1
  const redoNote =
    redoParts != null && redoParts > 0 ? ` · ${Math.round(redoParts)} redo` : ''
  return (
    <section className="shell kpis">
      <div className="core">
        <div className="kpi kpi-oee">
          <span className="label">
            <i className="dot" style={{ background: METRIC.oee }} />OEE
          </span>
          <span className="value">{pct(oee.oee)}</span>
        </div>
        <div className="kpi">
          <span className="label">
            <i className="dot" style={{ background: METRIC.availability }} />Kullanılabilirlik
          </span>
          <span className="value">{pct(oee.availability)}</span>
        </div>
        <div className="kpi">
          <span className="label">
            <i className="dot" style={{ background: METRIC.performance }} />Performans
          </span>
          <span className="value">{pct(oee.performance)}</span>
        </div>
        <div className="kpi">
          <span className="label">
            <i className="dot" style={{ background: METRIC.quality }} />Kalite (ilk-geçiş)
          </span>
          <span className="value">{pct(oee.quality)}</span>
          <span className="value small">
            <i className="dot" style={{ background: METRIC.finalYield }} />Nihai {pct(finalYield)}
            {redoNote}
          </span>
        </div>
        <div className="kpi">
          <span className="label">Veri güvenilirliği</span>
          <span className="value small">
            Mikro duruş girişi {pct(dq.microstop_entry_coverage)}
            <br />
            <span className="muted">tek manuel girdi; gerisi sistemce</span>
          </span>
        </div>
      </div>
    </section>
  )
}

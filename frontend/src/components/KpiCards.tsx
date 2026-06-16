// renderKpis karşılığı: OEE/A/P/Q + veri güvenilirliği özeti. .kpis tam genişlik kartı.
import type { DataQuality, Oee } from '../api/types'
import { pct } from '../styles/theme'

interface Props {
  oee: Oee
  dq: DataQuality
}

export default function KpiCards({ oee, dq }: Props) {
  return (
    <section className="shell kpis">
      <div className="core">
        <div className="kpi kpi-oee">
          <span className="label">OEE</span>
          <span className="value">{pct(oee.oee)}</span>
        </div>
        <div className="kpi">
          <span className="label">Kullanılabilirlik</span>
          <span className="value">{pct(oee.availability)}</span>
        </div>
        <div className="kpi">
          <span className="label">Performans</span>
          <span className="value">{pct(oee.performance)}</span>
        </div>
        <div className="kpi">
          <span className="label">Kalite</span>
          <span className="value">{pct(oee.quality)}</span>
        </div>
        <div className="kpi">
          <span className="label">Veri güvenilirliği</span>
          <span className="value small">
            Duruş {pct(dq.downtime_entry_coverage)} · Mikro {pct(dq.microstop_entry_coverage)}
          </span>
        </div>
      </div>
    </section>
  )
}

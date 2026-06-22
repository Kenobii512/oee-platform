// Replay canlı Control Strip: akış sırasında gauge sinematik kayar (Dial live), A/P/Q
// kanallar canlı dolar, biriken kayıp/kazanç + ilerleme barı. snap=null → pre-play.
import type { ReplaySnapshot } from '../api/types'
import { METRIC, num1, tl } from '../styles/theme'
import Dial from './Dial'

function RChannel({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="ctile">
      <span className="ck">
        <span className="sq" style={{ background: color }} />
        {label}
      </span>
      <div className="cv">
        {num1(value * 100)}
        <small>%</small>
      </div>
      <div className="meter">
        <i style={{ transform: `scaleX(${Math.min(1, value)})`, background: color }} />
      </div>
    </div>
  )
}

interface Props {
  snap: ReplaySnapshot | null
  progress: number
  running: boolean
  done: boolean
}

export default function ReplayHero({ snap, progress, running, done }: Props) {
  const o = snap?.oee
  const status = done ? '· final' : running ? '· canlı' : ''
  return (
    <section className="shell fhero replay-hero">
      <div className="core">
        <div className="cstrip">
          <div className="cs-gauge">
            <span className="gcap">OEE {status}</span>
            <Dial value={o ? o.oee : 0} live />
            <div className="gscale">
              <span>0</span>
              <span>HEDEF 85</span>
              <span>100</span>
            </div>
            <div className="rprog" aria-hidden="true">
              <i style={{ transform: `scaleX(${progress / 100})` }} />
            </div>
            <div className="rprog-cap">
              %{progress} · {snap ? snap.event_count : 0} olay {done ? '· tamamlandı' : ''}
            </div>
          </div>

          <div className="cs-cascade">
            <div className="cs-channels">
              <RChannel label="Kullanılabilirlik" value={o ? o.availability : 0} color={METRIC.availability} />
              <span className="cs-arrow" aria-hidden="true">→</span>
              <RChannel label="Performans" value={o ? o.performance : 0} color={METRIC.performance} />
              <span className="cs-arrow" aria-hidden="true">→</span>
              <RChannel label="Kalite (ilk-geçiş)" value={o ? o.quality : 0} color={METRIC.quality} />
            </div>

            <div className="cs-cost">
              <div className="cs-cost-main">
                <span className="cs-cost-k">Biriken kayıp</span>
                <strong>{snap ? `${tl(snap.cost.total_tl)} ₺` : '—'}</strong>
                {!snap && <span className="cs-cost-u">Oynat'a basın</span>}
              </div>
              <div className="cs-dq">
                Tahmini kazanç <strong>{snap ? `~${tl(snap.total_estimated_gain_tl)} ₺` : '—'}</strong>
                <span className="cs-dq-note">geri kazanılabilir üst sınır</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

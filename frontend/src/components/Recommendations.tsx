// Öneriler: TL azalan aksiyon listesi. Sıra no + kazanca oranlı etki çubuğu (görsel tarama),
// başlık, ~kazanç aralığı, aksiyon, kayıp + varsayım. inferred=indigo öncü nokta.
import type { Recommendations as RecData } from '../api/types'
import { METRIC, tl } from '../styles/theme'
import Card from './Card'
import Info from './Info'

export default function Recommendations({ rec }: { rec: RecData }) {
  const recs = rec.recommendations // zaten TL azalan sıralı (backend)
  const maxGain = Math.max(...recs.map((r) => r.estimated_gain_tl_high), 1)

  return (
    <Card eyebrow="Öneriler · Ne Yapmalı?" className="recommendations card-wide">
      <span className="muted">
        varsayım: geri kazanım oranları{' '}
        <Info text="Kaynak: config/recommend.yaml" />
      </span>
      <div className="kpi-line">
        <span className="muted">Tahmini toplam kazanç (üst sınır):</span>
        <strong>~{tl(rec.total_estimated_gain_tl)} TL</strong>
      </div>
      <span className="muted">
        Kazançlar üst sınır tahminidir ve kalemler arasında örtüşebilir (toplam, bağımsız kabul eder).
      </span>
      <ol className="rec-list">
        {recs.map((r, i) => (
          <li key={r.category} className={`rec${r.kind === 'inferred' ? ' inferred' : ''}`}>
            <div className="rec-head">
              <span className="rec-rank">{i + 1}</span>
              <span className="rec-title">{r.title}</span>
              <span className="rec-gain">
                ~{tl(r.estimated_gain_tl_low)}–{tl(r.estimated_gain_tl_high)} TL/dönem
              </span>
            </div>
            <div className="rec-impact" aria-hidden="true">
              <i
                style={{
                  width: `${(r.estimated_gain_tl_high / maxGain) * 100}%`,
                  background: r.kind === 'inferred' ? METRIC.performance : METRIC.availability,
                }}
              />
            </div>
            <p className="rec-action">{r.action}</p>
            <p className="muted rec-meta">
              Kayıp: <strong>{tl(r.tl)} TL</strong>
              {r.kind === 'inferred' ? ' · çıkarımsal' : ''} · {r.assumption}
            </p>
          </li>
        ))}
      </ol>
    </Card>
  )
}

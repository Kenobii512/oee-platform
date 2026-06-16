// renderRecommendations karşılığı: TL azalan öneri kartları (başlık, ~kazanç, aksiyon, kayıp+varsayım).
import type { Recommendations as RecData } from '../api/types'
import { tl } from '../styles/theme'
import Card from './Card'

export default function Recommendations({ rec }: { rec: RecData }) {
  const recs = rec.recommendations // zaten TL azalan sıralı (backend)

  return (
    <Card eyebrow="Öneriler · ne yapmalı" className="recommendations">
      <span className="muted">varsayım: geri-kazanım oranları config/recommend.yaml</span>
      <div className="kpi-line">
        <span className="muted">Tahmini toplam kazanç:</span>
        <strong>~{tl(rec.total_estimated_gain_tl)} TL</strong>
      </div>
      <ol className="rec-list">
        {recs.map((r) => (
          <li key={r.category} className={`rec${r.kind === 'inferred' ? ' inferred' : ''}`}>
            <div className="rec-head">
              <span className="rec-title">{r.title}</span>
              <span className="rec-gain">~{tl(r.estimated_gain_tl)} TL/dönem</span>
            </div>
            <p className="rec-action">{r.action}</p>
            <p className="muted rec-meta">
              Kayıp: <strong>{tl(r.tl)} TL</strong>
              {r.kind === 'inferred' ? ' · çıkarım' : ''} · {r.assumption}
            </p>
          </li>
        ))}
      </ol>
    </Card>
  )
}

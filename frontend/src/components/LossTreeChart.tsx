// Kayıp ağacı: yığılmış 100% oran çubuğu (her kaybın paya oranı bir bakışta).
// Renk kind'a göre (görünür=yeşil, çıkarımsal=indigo); çıkarımsal segmentler TARANMIŞ
// (renk-körü erişilebilirlik — renge ek desen). Absolut değerler etiket listesinde.
import type { LossCat } from '../api/types'
import { METRIC } from '../styles/theme'
import Card from './Card'

interface Props {
  eyebrow: string
  cats: LossCat[]
}

const fmt = (n: number) => Math.round(n).toLocaleString('tr-TR')

export default function LossTreeChart({ eyebrow, cats }: Props) {
  const total = cats.reduce((s, c) => s + c.value, 0)
  const color = (c: LossCat) => (c.kind === 'inferred' ? METRIC.performance : METRIC.availability)

  return (
    <Card eyebrow={eyebrow}>
      {total <= 0 ? (
        <p className="muted">Bu eksende kayıp yok.</p>
      ) : (
        <>
          <div
            className="proportion"
            role="img"
            aria-label={`Kayıp dağılımı: ${cats
              .map((c) => `${c.category} %${Math.round((c.value / total) * 100)}`)
              .join(', ')}`}
          >
            {cats.map((c) => (
              <span
                key={c.category}
                className={`prop-seg${c.kind === 'inferred' ? ' inf' : ''}`}
                style={{ width: `${(c.value / total) * 100}%`, background: color(c) }}
                title={`${c.category}: ${fmt(c.value)}`}
              />
            ))}
          </div>
          <ul className="prop-legend">
            {cats.map((c) => (
              <li key={c.category}>
                <span className={`sw${c.kind === 'inferred' ? ' inf' : ''}`} style={{ background: color(c) }} />
                <span className="nm">
                  {c.category}
                  {c.kind === 'inferred' && <em> · çıkarım</em>}
                </span>
                <span className="vl">{fmt(c.value)}</span>
                <span className="pc">%{Math.round((c.value / total) * 100)}</span>
              </li>
            ))}
          </ul>
          <p className="prop-note">
            <span className="sw" style={{ background: METRIC.availability }} /> görünür ·{' '}
            <span className="sw inf" style={{ background: METRIC.performance }} /> çıkarımsal (taranmış)
          </p>
        </>
      )}
    </Card>
  )
}

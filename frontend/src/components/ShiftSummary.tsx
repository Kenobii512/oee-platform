// Vardiya Künyesi: gözlem penceresi + parça sayıları (/oee bağlam alanları).
// "İyi (ilk geçiş)" = yüklenen − redo (Q'nun payıyla birebir; formül çoğaltma sayılmaz).
// good_count bilinçli gösterilmez: no-scrap modelinde ≈ yüklenen (kafa karıştırır).
import type { Oee } from '../api/types'
import { hm, num0 } from '../styles/theme'
import Card from './Card'

export default function ShiftSummary({ oee }: { oee: Oee }) {
  const { loaded_qty: loaded, redo_count: redo, span_min: span } = oee
  if (loaded == null || redo == null || span == null || loaded <= 0) return null
  return (
    <Card eyebrow="Vardiya Künyesi" period className="kunye">
      <dl className="kn-rows">
        <div className="kn-row">
          <dt>Gözlem penceresi</dt>
          <dd>{hm(span)}</dd>
        </div>
        <div className="kn-row kn-sep">
          <dt>Yüklenen</dt>
          <dd>{num0(loaded)} parça</dd>
        </div>
        <div className="kn-row">
          <dt>İyi (ilk geçiş)</dt>
          <dd>{num0(loaded - redo)} parça</dd>
        </div>
        <div className="kn-row">
          <dt>Redo</dt>
          <dd>{num0(redo)} parça</dd>
        </div>
      </dl>
    </Card>
  )
}

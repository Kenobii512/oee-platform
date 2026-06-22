// "Vardiya Künyesi": backend'in hesaplayıp daha önce panoda gösterilmeyen bağlam metrikleri
// (kullanım, gözlem penceresi, ham parça sayıları). Detay görünümüne özel (ikincil kullanıcı).
// OEE'yi etkilemez; etiket/değer satırları, tabular-mono değerler.
import type { Oee } from '../api/types'
import { hm, int, pct } from '../styles/theme'
import Card from './Card'
import Info from './Info'

export default function ShiftSummary({ oee }: { oee: Oee }) {
  const rows: Array<{ key: string; label: React.ReactNode; value: string }> = [
    {
      key: 'util',
      label: (
        <>
          Kullanım{' '}
          <Info text="Planlı duruş dahil takvim zamanına göre makinenin çalışma oranı. Kullanılabilirlik'ten farklıdır (o planlı duruşu hariç tutar)." />
        </>
      ),
      value: oee.utilization != null ? pct(oee.utilization) : '—',
    },
    { key: 'span', label: 'Gözlem penceresi', value: oee.span_min != null ? hm(oee.span_min) : '—' },
    { key: 'loaded', label: 'Yüklenen', value: oee.loaded_qty != null ? int(oee.loaded_qty) : '—' },
    { key: 'good', label: 'İyi', value: oee.good_count != null ? int(oee.good_count) : '—' },
    { key: 'redo', label: 'Redo', value: oee.redo_count != null ? int(oee.redo_count) : '—' },
  ]
  return (
    <Card eyebrow="Vardiya Künyesi" period>
      <dl className="kunye">
        {rows.map((r) => (
          <div className="kunye-row" key={r.key}>
            <dt>{r.label}</dt>
            <dd>{r.value}</dd>
          </div>
        ))}
      </dl>
    </Card>
  )
}

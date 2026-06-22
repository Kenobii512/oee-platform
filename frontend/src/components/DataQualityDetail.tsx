// #dq-detail + açıklama notu karşılığı: operatör neden-giriş kapsamı.
import type { DataQuality } from '../api/types'
import { pct } from '../styles/theme'
import Card from './Card'

export default function DataQualityDetail({ dq }: { dq: DataQuality }) {
  return (
    <Card eyebrow="Veri Güvenilirliği" period>
      <div className="dq-detail">
        Tek manuel girdi: <strong>mikro duruş</strong>. Duruş, hız, doluluk ve kalite
        sistemce (PLC/sayaç/kalite istasyonu) otomatik ölçülür.
        <br />• Mikro duruş giriş kapsamı: <strong>{pct(dq.microstop_entry_coverage)}</strong>{' '}
        <span className="muted">
          (düşük olması beklenir: operatör çoğunu girmez, Excel/manuel takibe karşı asıl fark)
        </span>
      </div>
      <p className="muted">
        <strong>Çıkarımsal</strong> (taranmış) segmentler gerçek veride yoktur; genel veriden
        kestirilir. Farklı eksenler (dakika ↔ parça) olduğundan tek Pareto yapılmaz; ortak birim
        (TL) Maliyet Pareto'sundadır.
      </p>
    </Card>
  )
}

// #dq-detail + açıklama notu karşılığı: operatör neden-giriş kapsamı.
import type { DataQuality } from '../api/types'
import { pct } from '../styles/theme'
import Card from './Card'

export default function DataQualityDetail({ dq }: { dq: DataQuality }) {
  return (
    <Card eyebrow="Veri Güvenilirliği" period>
      <div className="dq-detail">
        Operatör neden-giriş kapsamı:
        <br />• DOWNTIME: <strong>{pct(dq.downtime_entry_coverage)}</strong>
        <br />• MICROSTOP: <strong>{pct(dq.microstop_entry_coverage)}</strong>{' '}
        <span className="muted">(mikro duruşta düşük olması beklenir — içgörü, kusur değil)</span>
      </div>
      <p className="muted">
        Mor çubuklar <strong>çıkarım</strong> kanallarıdır (gerçek veride yok, genel veriden
        kestirilir). Farklı eksenler (dakika vs parça) olduğundan tek Pareto yapılmaz; ortak birim
        (TL) Maliyet Pareto'sunda.
      </p>
    </Card>
  )
}

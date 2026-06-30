// Backend JSON sözleşmesi (oee-platform/backend). Tek doğruluk kaynağı API; bu tipler onu yansıtır.

export type Axis = 'minutes' | 'parts'
export type Kind = 'visible' | 'inferred'

export interface Oee {
  oee: number
  availability: number
  performance: number
  quality: number // ilk-geçiş kalite (first_pass) — OEE'nin Q'su
  final_yield?: number // Σ good / Σ loaded (no-scrap → ≈%100)
  utilization?: number
  planned_downtime_min?: number
}

export interface LossCat {
  category: string
  axis: Axis
  value: number
  kind: Kind
}

export interface LossTree {
  categories: LossCat[]
}

export interface CostCat {
  category: string
  axis: Axis
  value: number
  tl: number
  kind: Kind
  // H3 belirsizlik: çıkarım kanallarında nokta TL etrafında bant + güven skoru.
  tl_low?: number
  tl_high?: number
  confidence?: number
  low_confidence?: boolean
}

export interface CostTree {
  categories: CostCat[]
  total_tl: number
}

export interface Recommendation {
  category: string
  axis: Axis
  value: number
  kind: Kind
  tl: number
  estimated_gain_tl: number // nokta tahmin (üst/iyimser sınır)
  estimated_gain_tl_low: number // aralık alt sınırı
  estimated_gain_tl_high: number // aralık üst sınırı (= estimated_gain_tl)
  recovery_ratio: number
  title: string
  action: string
  assumption: string
  low_confidence?: boolean // H3: kayıp kaleminin veri-güveni düşük (öneride uyarı)
}

export interface Recommendations {
  recommendations: Recommendation[]
  total_estimated_gain_tl: number
}

export interface TrendPoint {
  period: string
  oee: number
  availability: number
  performance: number
  quality: number // ilk-geçiş kalite
  final_yield: number // nihai verim (no-scrap → ≈%100)
}

export interface DataQuality {
  // G10: operatörün tek manuel girdisi mikro duruş (duruş sistemce otomatik bilinir).
  microstop_entry_coverage: number
}

export interface ScenarioInfo {
  id: string
  title: string
  description: string
  expected_top_loss: string
  narrative?: string // H6: bir cümlelik demo hikâyesi
  highlight?: string // H6: vurgulanacak grafik (cost | loss_tree | trend | oee)
}

export interface ScenarioCatalog {
  scenarios: ScenarioInfo[]
}

/** Tarih filtresi: ISO-benzeri "YYYY-MM-DD HH:MM" (datetime-local 'T' → boşluk). */
export interface Range {
  from?: string
  to?: string
}

/** G7 replay snapshot'ı (SSE /replay/stream — büyüyen 'şimdiye kadar' penceresi). */
export interface ReplaySnapshot {
  to: string | null
  oee: { oee: number; availability: number; performance: number; quality: number }
  cost: CostTree
  total_estimated_gain_tl: number
  event_count: number
}

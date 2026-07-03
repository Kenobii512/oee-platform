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
  calendar_min?: number | null // H8: utilization paydası (takvim dk); şeffaflık için
  // Vardiya künyesi bağlamı (spec 2026-07-03); eski backend yanıtlarında bulunmayabilir.
  loaded_qty?: number
  good_count?: number // nihai iyi; kartta gösterilmez (no-scrap → ≈yüklenen)
  redo_count?: number
  span_min?: number // gözlem penceresi (dk)
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
  // QC/H1+H3: veri-yeterlilik (pencerede çıkarım/OEE güvenilir mi).
  sufficient?: boolean
  sufficiency_score?: number // 0..1
  event_count?: number
  span_min?: number
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
  active?: string | null // açılış auto-ingest'i ya da son aktivasyon (pano başlangıç seçimi)
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

// What-if analitiği (GET /whatif): azaltım oranları → önce/sonra + TL kazanç.
export interface WhatIfComponents {
  availability: number
  performance: number
  quality: number
  oee: number
}

export interface WhatIfGainItem {
  category: string
  reduction: number
  gain_tl: number
  gain_tl_low: number
  gain_tl_high: number
  kind: Kind
}

export interface WhatIfResult {
  baseline: WhatIfComponents
  adjusted: WhatIfComponents
  gain: {
    total_tl: number
    total_tl_low: number
    total_tl_high: number
    per_category: WhatIfGainItem[]
  }
}

/** Slider anahtarları — /whatif query paramlarıyla birebir. */
export type WhatIfReductions = {
  downtime: number
  microstop: number
  speed_loss: number
  quality_redo: number
  fill_loss: number
}

// Canlı hat animasyonu (GET /replay/timeline): hat tanımı + ham olay dökümü.
export interface TimelineEvent {
  timestamp: string // "YYYY-MM-DD HH:MM:SS.sss"
  carrier_id: string | null
  station_id: string | null // tank id | "HOIST" | null (LOAD/UNLOAD/QC/STRIP)
  event_type: string // LOAD|MOVE|PROCESS|OVER_RESIDENCE|UNLOAD|QC|STRIP|DOWNTIME|MICROSTOP
  duration: number // dakika
  reason_code: string | null
}

export interface ReplayTimeline {
  line: { id: string; name: string }[]
  events: TimelineEvent[]
}

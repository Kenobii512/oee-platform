// Backend JSON sözleşmesi (oee-platform/backend). Tek doğruluk kaynağı API; bu tipler onu yansıtır.

export type Axis = 'minutes' | 'parts'
export type Kind = 'visible' | 'inferred'

export interface Oee {
  oee: number
  availability: number
  performance: number
  quality: number
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
  estimated_gain_tl: number
  recovery_ratio: number
  title: string
  action: string
  assumption: string
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
  quality: number
}

export interface DataQuality {
  downtime_entry_coverage: number
  microstop_entry_coverage: number
}

export interface ScenarioInfo {
  id: string
  title: string
  description: string
  expected_top_loss: string
}

export interface ScenarioCatalog {
  scenarios: ScenarioInfo[]
}

/** Tarih filtresi: ISO-benzeri "YYYY-MM-DD HH:MM" (datetime-local 'T' → boşluk). */
export interface Range {
  from?: string
  to?: string
}

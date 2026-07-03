// API istemcisi — mevcut Jinja panosunun fetch mantığını yansıtır (qs, getJSON).
// from/to: datetime-local 'T' → boşluk (backend "YYYY-MM-DD HH:MM" bekler).
import type {
  CostTree,
  DataQuality,
  LossTree,
  Oee,
  Range,
  Recommendations,
  ReplayTimeline,
  ScenarioCatalog,
  TrendPoint,
  WhatIfReductions,
  WhatIfResult,
} from './types'

export function qs(range: Range = {}): string {
  const p = new URLSearchParams()
  if (range.from) p.set('from', range.from.replace('T', ' '))
  if (range.to) p.set('to', range.to.replace('T', ' '))
  const s = p.toString()
  return s ? `?${s}` : ''
}

export async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(path)
  if (!r.ok) {
    // Backend hataları {detail: "..."} döndürür (H9); kullanıcıya jenerik durum yerine mesajı göster.
    const body = (await r.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `${path} -> ${r.status}`)
  }
  return r.json() as Promise<T>
}

export const api = {
  oee: (range?: Range) => getJSON<Oee>(`/oee${qs(range)}`),
  lossTree: (range?: Range) => getJSON<LossTree>(`/loss-tree${qs(range)}`),
  cost: (range?: Range) => getJSON<CostTree>(`/loss-tree/cost${qs(range)}`),
  recommendations: (range?: Range) =>
    getJSON<Recommendations>(`/recommendations${qs(range)}`),
  trend: (range?: Range) => {
    const r = qs(range)
    const sep = r ? '&' : '?'
    return getJSON<TrendPoint[]>(`/oee/trend${r}${sep}bucket=day`)
  },
  dataQuality: () => getJSON<DataQuality>('/data-quality/summary'),
  scenarios: () => getJSON<ScenarioCatalog>('/scenarios'),
  replayTimeline: (scenario: string) =>
    getJSON<ReplayTimeline>(`/replay/timeline?scenario=${encodeURIComponent(scenario)}`),
  whatif: (red: WhatIfReductions, range?: Range) => {
    const r = qs(range)
    const p = new URLSearchParams(r ? r.slice(1) : '')
    for (const [k, v] of Object.entries(red)) if (v > 0) p.set(k, String(v))
    const q = p.toString()
    return getJSON<WhatIfResult>(`/whatif${q ? `?${q}` : ''}`)
  },
  activateScenario: async (id: string): Promise<void> => {
    const r = await fetch(`/scenarios/${id}/activate`, { method: 'POST' })
    if (!r.ok) throw new Error(`activate ${id} -> ${r.status}`)
  },
}

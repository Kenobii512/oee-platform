// Canlı hat şeridinin durum-indirgeyicisi: /replay/timeline olay dökümünden sanal an t
// için hat durumunu türetir. SAF — DOM/React yok; vitest'le derin test edilir.
// Redo gerçeği: UNLOAD→QC→STRIP(station boş)→yeniden LOAD→tam ikinci tur. Vinç duruşunda
// donma AYRICA modellenmez: olay damgaları duruş gecikmesini zaten taşır (emergent).
import type { ReplayTimeline, TimelineEvent } from '../api/types'

export const YUKLEME = 'YUKLEME' // sol uç kapak (pseudo-istasyon)
export const CIKIS = 'CIKIS' // sağ uç kapak (QC / boşaltma)

export type CarrierPos =
  | { kind: 'tankta'; station: string }
  | { kind: 'tasiniyor'; from: string; to: string; progress: number }
  | { kind: 'bekliyor'; station: string }
  | { kind: 'strip'; progress: number } // QC red → söküm; çıkıştan yüklemeye geri dönüş
  | { kind: 'cikti' }

export interface CarrierState {
  id: string
  pos: CarrierPos
  redo: boolean
}

export interface TankState {
  id: string
  name: string
  durum: 'bos' | 'isliyor' | 'bekliyor' | 'mikro' | 'durus'
  carrier?: string
  reason?: string
}

export interface HoistState {
  durum: 'bos' | 'tasiyor' | 'durus'
  carrier?: string
  from?: string
  to?: string
  progress?: number
  reason?: string
}

export interface LineState {
  tanks: TankState[]
  hoist: HoistState
  carriers: CarrierState[]
  yuklenen: number
  cikan: number
  redo: number
}

/** Backend "YYYY-MM-DD HH:MM:SS[.ffffff]" → epoch ms (tüm damgalar aynı saat dilimi).
 *  Python str(datetime) 6 haneli mikrosaniye yazabilir; Date için >3 kesir hanesi
 *  implementation-defined → kesir 3 haneye kırpılır. */
export const tsMs = (s: string): number =>
  new Date(s.replace(' ', 'T').replace(/(\.\d{3})\d+$/, '$1')).getTime()

interface Ev {
  t0: number
  t1: number
  e: TimelineEvent
}

export interface Timeline {
  line: { id: string; name: string }[]
  byCarrier: Map<string, Ev[]>
  byStation: Map<string, Ev[]> // DOWNTIME/MICROSTOP (HOIST dahil)
  loads: number[]
  unloads: number[]
  strips: number[]
  t0: number
  t1: number
}

export function buildTimeline(payload: ReplayTimeline): Timeline {
  const byCarrier = new Map<string, Ev[]>()
  const byStation = new Map<string, Ev[]>()
  const loads: number[] = []
  const unloads: number[] = []
  const strips: number[] = []
  let t0 = Infinity
  let t1 = -Infinity
  for (const e of payload.events) {
    const start = tsMs(e.timestamp)
    const ev: Ev = { t0: start, t1: start + e.duration * 60_000, e }
    t0 = Math.min(t0, ev.t0)
    t1 = Math.max(t1, ev.t1)
    if (e.event_type === 'DOWNTIME' || e.event_type === 'MICROSTOP') {
      const st = e.station_id ?? ''
      if (!byStation.has(st)) byStation.set(st, [])
      byStation.get(st)!.push(ev)
      continue
    }
    if (!e.carrier_id) continue
    if (e.event_type === 'LOAD') loads.push(start)
    if (e.event_type === 'UNLOAD') unloads.push(start)
    if (e.event_type === 'STRIP') strips.push(start)
    if (!byCarrier.has(e.carrier_id)) byCarrier.set(e.carrier_id, [])
    byCarrier.get(e.carrier_id)!.push(ev)
  }
  return { line: payload.line, byCarrier, byStation, loads, unloads, strips, t0, t1 }
}

/** Sıralı dizide t'den küçük-eşit eleman sayısı (sayaçlar için). */
const countLE = (sorted: number[], t: number): number => {
  let lo = 0
  let hi = sorted.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (sorted[mid] <= t) lo = mid + 1
    else hi = mid
  }
  return lo
}

const clamp01 = (x: number): number => Math.max(0, Math.min(1, x))

/** MOVE'un kalkış istasyonu: geriye doğru ilk PROCESS/OVER_RESIDENCE; yoksa yükleme. */
function moveFrom(evs: Ev[], i: number): string {
  for (let j = i - 1; j >= 0; j--) {
    const e = evs[j].e
    if (e.event_type === 'PROCESS' || e.event_type === 'OVER_RESIDENCE') return e.station_id!
    if (e.event_type === 'LOAD') return YUKLEME
  }
  return YUKLEME
}

/** MOVE'un varış istasyonu: ileriye doğru ilk PROCESS; yoksa çıkış. */
function moveTo(evs: Ev[], i: number): string {
  for (let j = i + 1; j < evs.length; j++) {
    const e = evs[j].e
    if (e.event_type === 'PROCESS') return e.station_id!
    if (e.event_type === 'UNLOAD' || e.event_type === 'QC') return CIKIS
  }
  return CIKIS
}

/** İki olay arasındaki boşlukta konum: i = t'den önce biten son olayın indeksi. */
function gapPos(evs: Ev[], i: number): CarrierPos | null {
  for (let j = i; j >= 0; j--) {
    const e = evs[j].e
    switch (e.event_type) {
      case 'PROCESS':
      case 'OVER_RESIDENCE':
        return { kind: 'bekliyor', station: e.station_id! } // vinç bekleniyor
      case 'MOVE':
        return { kind: 'tankta', station: moveTo(evs, j) } // vinç bıraktı, işlem başlamadı
      case 'LOAD':
        return { kind: 'tasiniyor', from: YUKLEME, to: YUKLEME, progress: 0 } // askıda, ilk MOVE bekleniyor
      case 'STRIP':
        return { kind: 'strip', progress: 1 } // söküm bitti, yeniden LOAD bekleniyor
      case 'UNLOAD':
      case 'QC':
        return { kind: 'cikti' }
    }
  }
  return null
}

/** Askının t anındaki konumu; hatta hiç girmemişse null. */
function carrierPosAt(evs: Ev[], t: number): CarrierPos | null {
  if (evs.length === 0 || t < evs[0].t0) return null
  for (let i = 0; i < evs.length; i++) {
    const { t0, t1, e } = evs[i]
    if (t < t0) return gapPos(evs, i - 1)
    if (t < t1) {
      switch (e.event_type) {
        case 'PROCESS':
          return { kind: 'tankta', station: e.station_id! }
        case 'OVER_RESIDENCE':
          return { kind: 'bekliyor', station: e.station_id! }
        case 'MOVE':
          return {
            kind: 'tasiniyor',
            from: moveFrom(evs, i),
            to: moveTo(evs, i),
            progress: clamp01((t - t0) / (t1 - t0 || 1)),
          }
        case 'STRIP':
          return { kind: 'strip', progress: clamp01((t - t0) / (t1 - t0 || 1)) }
        default:
          break // LOAD/UNLOAD/QC anlıktır (duration 0); boşluk mantığı halleder
      }
    }
  }
  return gapPos(evs, evs.length - 1)
}

export function lineStateAt(tl: Timeline, tMs: number): LineState {
  const t = Math.max(tl.t0, Math.min(tl.t1, tMs)) // pencere kıskacı
  const carriers: CarrierState[] = []
  for (const [id, evs] of tl.byCarrier) {
    const pos = carrierPosAt(evs, t)
    if (!pos || pos.kind === 'cikti') continue // sahnede değil
    const redo = evs.some((ev) => ev.e.event_type === 'STRIP' && ev.t0 <= t)
    carriers.push({ id, pos, redo })
  }

  let hoist: HoistState = { durum: 'bos' }
  const hoistDown = (tl.byStation.get('HOIST') ?? []).find(
    (ev) => ev.e.event_type === 'DOWNTIME' && ev.t0 <= t && t < ev.t1,
  )
  if (hoistDown) {
    hoist = { durum: 'durus', reason: hoistDown.e.reason_code ?? undefined }
  } else {
    const moving = carriers.find((c) => c.pos.kind === 'tasiniyor' && c.pos.from !== c.pos.to)
    if (moving && moving.pos.kind === 'tasiniyor') {
      hoist = {
        durum: 'tasiyor',
        carrier: moving.id,
        from: moving.pos.from,
        to: moving.pos.to,
        progress: moving.pos.progress,
      }
    }
  }

  // Öncelik: DOWNTIME > MICROSTOP > bekliyor(OVER_RESIDENCE/boşluk) > işliyor > boş.
  const tanks: TankState[] = tl.line.map((tk) => {
    const st = tl.byStation.get(tk.id) ?? []
    const down = st.find((ev) => ev.e.event_type === 'DOWNTIME' && ev.t0 <= t && t < ev.t1)
    if (down) return { ...tk, durum: 'durus', reason: down.e.reason_code ?? undefined }
    const micro = st.find((ev) => ev.e.event_type === 'MICROSTOP' && ev.t0 <= t && t < ev.t1)
    if (micro) return { ...tk, durum: 'mikro' }
    const waiting = carriers.find((c) => c.pos.kind === 'bekliyor' && c.pos.station === tk.id)
    if (waiting) return { ...tk, durum: 'bekliyor', carrier: waiting.id }
    const busy = carriers.find((c) => c.pos.kind === 'tankta' && c.pos.station === tk.id)
    if (busy) return { ...tk, durum: 'isliyor', carrier: busy.id }
    return { ...tk, durum: 'bos' }
  })

  return {
    tanks,
    hoist,
    carriers,
    yuklenen: countLE(tl.loads, t),
    cikan: countLE(tl.unloads, t),
    redo: countLE(tl.strips, t),
  }
}

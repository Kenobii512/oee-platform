import { describe, expect, it } from 'vitest'

import type { ReplayTimeline, TimelineEvent } from '../api/types'
import { CIKIS, YUKLEME, buildTimeline, lineStateAt, tsMs } from './replayLine'

// Kurgu hat: 2 tank. Zaman eksenini okunur tutmak için dakika ofsetli damga üretici.
const T0 = Date.parse('2026-01-05T06:00:00.000')
const at = (min: number): string => {
  const d = new Date(T0 + min * 60_000)
  const p = (n: number, w = 2) => String(n).padStart(w, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}`
}
const ev = (
  min: number, type: string, opts: Partial<TimelineEvent> = {},
): TimelineEvent => ({
  timestamp: at(min), carrier_id: null, station_id: null,
  event_type: type, duration: 0, reason_code: null, ...opts,
})

const LINE = [{ id: 'tankA', name: 'Tank A' }, { id: 'tankB', name: 'Tank B' }]
// c1 güzergâhı: LOAD@0 → MOVE(0.5) → tankA PROCESS@0.5(2dk) → [boşluk] → MOVE@3(0.5)
// → tankB PROCESS@3.5(1dk) → MOVE@4.5(0.5) → UNLOAD/QC@5 → STRIP@5(2dk) → LOAD@8 (redo turu)
const EVENTS: TimelineEvent[] = [
  ev(0, 'LOAD', { carrier_id: 'CAR-0001' }),
  ev(0, 'MOVE', { carrier_id: 'CAR-0001', station_id: 'HOIST', duration: 0.5 }),
  ev(0.5, 'PROCESS', { carrier_id: 'CAR-0001', station_id: 'tankA', duration: 2 }),
  ev(3, 'MOVE', { carrier_id: 'CAR-0001', station_id: 'HOIST', duration: 0.5 }),
  ev(3.5, 'PROCESS', { carrier_id: 'CAR-0001', station_id: 'tankB', duration: 1 }),
  ev(4.5, 'MOVE', { carrier_id: 'CAR-0001', station_id: 'HOIST', duration: 0.5 }),
  ev(5, 'UNLOAD', { carrier_id: 'CAR-0001' }),
  ev(5, 'QC', { carrier_id: 'CAR-0001' }),
  ev(5, 'STRIP', { carrier_id: 'CAR-0001', duration: 2 }),
  ev(8, 'LOAD', { carrier_id: 'CAR-0001' }),
  ev(8, 'MOVE', { carrier_id: 'CAR-0001', station_id: 'HOIST', duration: 0.5 }),
  ev(8.5, 'PROCESS', { carrier_id: 'CAR-0001', station_id: 'tankA', duration: 2 }),
  // İstasyon olayları (carrier'sız):
  ev(10, 'DOWNTIME', { station_id: 'tankB', duration: 5, reason_code: 'rectifier_ariza' }),
  ev(11, 'MICROSTOP', { station_id: 'tankA', duration: 1 }),
  ev(16, 'DOWNTIME', { station_id: 'HOIST', duration: 3, reason_code: 'hoist_ariza' }),
]
const TL = buildTimeline({ line: LINE, events: EVENTS } as ReplayTimeline)
const t = (min: number) => T0 + min * 60_000

describe('tsMs', () => {
  it('backend damgasını epoch ms yapar', () => {
    expect(tsMs('2026-01-05 06:01:00.000')).toBe(T0 + 60_000)
  })
})

describe('lineStateAt — askı konumları', () => {
  it('PROCESS penceresinde tankta', () => {
    const s = lineStateAt(TL, t(1))
    expect(s.carriers).toHaveLength(1)
    expect(s.carriers[0].pos).toEqual({ kind: 'tankta', station: 'tankA' })
    expect(s.tanks.find((x) => x.id === 'tankA')?.durum).toBe('isliyor')
    expect(s.yuklenen).toBe(1)
  })

  it('MOVE ortasında tasiniyor, progress≈0.5; vinç tasiyor', () => {
    const s = lineStateAt(TL, t(3.25))
    const pos = s.carriers[0].pos
    expect(pos.kind).toBe('tasiniyor')
    if (pos.kind === 'tasiniyor') {
      expect(pos.from).toBe('tankA')
      expect(pos.to).toBe('tankB')
      expect(pos.progress).toBeCloseTo(0.5, 1)
    }
    expect(s.hoist.durum).toBe('tasiyor')
    expect(s.hoist.carrier).toBe('CAR-0001')
  })

  it('PROCESS bitti vinç gelmedi → bekliyor (boşluk)', () => {
    const s = lineStateAt(TL, t(2.75)) // PROCESS 2.5'te bitti, MOVE 3'te
    expect(s.carriers[0].pos).toEqual({ kind: 'bekliyor', station: 'tankA' })
    expect(s.tanks.find((x) => x.id === 'tankA')?.durum).toBe('bekliyor')
  })

  it('ilk MOVE yüklemeden gelir', () => {
    const s = lineStateAt(TL, t(0.25))
    const pos = s.carriers[0].pos
    if (pos.kind === 'tasiniyor') expect(pos.from).toBe(YUKLEME)
    else expect.unreachable('tasiniyor bekleniyordu')
  })

  it('son MOVE çıkışa gider', () => {
    const s = lineStateAt(TL, t(4.75))
    const pos = s.carriers[0].pos
    if (pos.kind === 'tasiniyor') expect(pos.to).toBe(CIKIS)
    else expect.unreachable('tasiniyor bekleniyordu')
  })

  it('STRIP penceresi: strip konumu + redo işareti + sayaçlar', () => {
    const s = lineStateAt(TL, t(6)) // STRIP 5→7
    expect(s.carriers[0].pos.kind).toBe('strip')
    expect(s.carriers[0].redo).toBe(true)
    expect(s.cikan).toBe(1)
    expect(s.redo).toBe(1)
  })

  it('redo turu: yeniden LOAD sonrası tankta, redo=true', () => {
    const s = lineStateAt(TL, t(9))
    expect(s.carriers[0].pos).toEqual({ kind: 'tankta', station: 'tankA' })
    expect(s.carriers[0].redo).toBe(true)
    expect(s.yuklenen).toBe(2) // iki LOAD
  })
})

describe('lineStateAt — istasyon durumları ve öncelik', () => {
  it('DOWNTIME > her şey: tank kırmızı + neden', () => {
    const s = lineStateAt(TL, t(12))
    const b = s.tanks.find((x) => x.id === 'tankB')!
    expect(b.durum).toBe('durus')
    expect(b.reason).toBe('rectifier_ariza')
  })

  it('MICROSTOP penceresinde mikro', () => {
    const s = lineStateAt(TL, t(11.5))
    expect(s.tanks.find((x) => x.id === 'tankA')?.durum).toBe('mikro')
  })

  it('HOIST DOWNTIME → vinç durus + neden', () => {
    const s = lineStateAt(TL, t(17))
    expect(s.hoist).toMatchObject({ durum: 'durus', reason: 'hoist_ariza' })
  })
})

describe('lineStateAt — pencere kıskacı', () => {
  it('pencereden önce/sonra uçlara kıskaçlanır', () => {
    expect(lineStateAt(TL, 0).yuklenen).toBe(1) // t0'a kıskaç (ilk LOAD anı)
    const end = lineStateAt(TL, t(999))
    expect(end.yuklenen).toBe(2)
    expect(end.redo).toBe(1)
  })
})

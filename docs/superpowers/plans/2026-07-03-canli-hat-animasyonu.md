# Canlı Hat Animasyonu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replay görünümüne SSE sanal saatine senkron canlı hat şeridi: tanklar, vinç rayı, hareket eden askı çipleri; duruşta kırmızı, redo'da geri dönüş.

**Architecture:** Yeni hafif uç `GET /replay/timeline` ham olay dökümü + hat tanımını bir kez verir (iş kuralı yok, `/replay/stream` izolasyon deseni). Frontend'te saf indirgeyici `lineStateAt(timeline, t)` sanal an t için hat durumunu türetir; `useVirtualClock` SSE snapshot'larının `to` damgasına lineer yaklaşan rAF saati üretir; `LineStrip` SVG bileşeni durumu çizer. rAF yeniden-render'ı yalnız LineStrip içindedir (Chart.js kartları etkilenmez).

**Tech Stack:** FastAPI + DuckDB in-memory (backend), React + TypeScript + SVG + vitest (frontend), Foundry Gauge tasarım dili (DESIGN.md token'ları).

**Spec:** `docs/superpowers/specs/2026-07-03-canli-hat-animasyonu-design.md`

## Global Constraints

- Branch: `feat/hat-animasyonu` (açık; spec commit'li `5296fe0`).
- SSE (`/replay/stream`) şeması ve davranışı DEĞİŞMEZ. Backend'de istasyon-durum hesabı YOK (timeline ham döküm).
- FIREWALL: timeline ucu ground_truth ALMAZ, paylaşılan repo'yu DEĞİŞTİRMEZ (in-memory DuckDB, stream ile aynı desen).
- Tank adları/sırası frontend'e GÖMÜLMEZ — uçtan gelen `line` listesi kullanılır.
- Foundry Gauge dili: keskin köşe, hairline `var(--line)`, tabular-nums, GLOW YOK, yaylanma/bounce YOK; durum renk geçişleri ~150ms.
- Duruş nedenleri Türkçe: `hoist_ariza`→"Vinç arızası", `rectifier_ariza`→"Redresör arızası", `furnace_ariza`→"Fırın arızası"; bilinmeyen kodda ham koda düşülür.
- Redo gerçeği (fixture'dan doğrulandı): `UNLOAD → QC → STRIP(≈6 dk, station boş) → yeniden LOAD → tam ikinci tur`. "Geri dönüş" animasyonu = STRIP penceresinde çipin çıkıştan yüklemeye kesikli yol üzerinde geri taşınması.
- Görsel kabul ölçütleri (spec): 1280px'te tek satır okunur; tank adları kısaltılmasız; 60fps akıcı; duruş kırmızısı (#a8443a değil — duruş için `--loss` kullanılır ama kalite mercanıyla karışmasın diye dolgu+etiket kombinasyonu farklı); mobilde (≤768px) şerit kendi kutusunda yatay kaydırmalı.
- `frontend_dist` git'e COMMIT EDİLMEZ (gitignore'da; Docker/Render kendi build'ini yapar).
- Commit mesajı gövdesi şu satırla biter: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- Komutlar (Windows Git Bash): backend `cd backend && pytest -q`, lint `cd backend && ruff check .`; frontend `cd frontend && npm run test|build|lint`.

---

### Task 1: Backend — `GET /replay/timeline`

**Files:**
- Modify: `backend/app/api/replay_routes.py` (senaryo çözümü helper'a çıkar + yeni uç)
- Test: `backend/tests/test_replay_timeline.py` (yeni)

**Interfaces:**
- Consumes: mevcut `load_scenario_catalog`, `load_line_definition` (tanks: `TankDef.id/.name`), `DuckDBRepository`, `load_csv_dir`.
- Produces: `GET /replay/timeline?scenario=` → `{"line": [{"id": str, "name": str}...],
  "events": [{"timestamp": str, "carrier_id": str|null, "station_id": str|null,
  "event_type": str, "duration": float, "reason_code": str|null}...]}` — events zaman sıralı. Task 2/4 frontend bunları okur.

- [ ] **Step 1: Failing testler**

Create `backend/tests/test_replay_timeline.py`:

```python
"""GET /replay/timeline: hat tanımı + zaman-sıralı ham olay dökümü; izolasyon; 404.
Canlı hat animasyonunun veri beslemesi — iş kuralı YOK, frontend indirgeyici tüketir."""
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIX = Path(__file__).resolve().parent / "fixtures" / "baseline"


def test_timeline_returns_line_and_sorted_events(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "tl.duckdb"))
    with TestClient(app) as client:
        r = client.get("/replay/timeline?scenario=baseline")
        assert r.status_code == 200
        body = r.json()
        # Hat YAML sırasında gelir; adlar frontend'e gömülmez.
        ids = [t["id"] for t in body["line"]]
        assert ids[0] == "yagsizlandirma" and ids[-1] == "kurutma"
        assert all(set(t) == {"id", "name"} and t["name"] for t in body["line"])
        evs = body["events"]
        assert len(evs) > 100
        assert set(evs[0]) == {
            "timestamp", "carrier_id", "station_id", "event_type", "duration", "reason_code",
        }
        stamps = [e["timestamp"] for e in evs]
        assert stamps == sorted(stamps)
        types = {e["event_type"] for e in evs}
        assert {"LOAD", "MOVE", "PROCESS", "UNLOAD"} <= types


def test_timeline_unknown_scenario_404(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "tl404.duckdb"))
    with TestClient(app) as client:
        r = client.get("/replay/timeline?scenario=yok_boyle")
        assert r.status_code == 404


def test_timeline_does_not_mutate_dashboard(tmp_path, monkeypatch):
    """İzolasyon: timeline (in-memory) paylaşılan DB'yi/pano /oee'yi değiştirmemeli."""
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "tliso.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(FIX)})
        before = client.get("/oee").json()
        client.get("/replay/timeline?scenario=breakdown_storm")
        after = client.get("/oee").json()
        assert before == after
```

- [ ] **Step 2: Testlerin başarısız olduğunu gör**

Run: `cd backend && pytest tests/test_replay_timeline.py -q`
Expected: FAIL — 404/405 (uç yok).

- [ ] **Step 3: Implementasyon**

`backend/app/api/replay_routes.py` — `replay_stream` içindeki senaryo çözümünü helper'a çıkar ve yeni ucu ekle. `replay_stream`'in ilk 8 satırı (cfg…data_dir kontrolü) şu çağrıyla değişir: `cfg, data_dir = _resolve_scenario_dir(request, scenario)`. Eklenecek kod (router tanımından sonra):

```python
def _resolve_scenario_dir(request: Request, scenario: str):
    """Senaryo id → (cfg, veri klasörü); bilinmeyen senaryo/klasör 404. stream+timeline ortak."""
    cfg = request.app.state.config
    cat = {s.id: s for s in load_scenario_catalog(cfg.scenario_config_path)}
    info = cat.get(scenario)
    if info is None:
        raise HTTPException(status_code=404, detail=f"bilinmeyen senaryo: {scenario}")
    data_dir = (_BACKEND_ROOT / info.data_dir).resolve()
    if not data_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"veri yok: {info.data_dir}")
    return cfg, data_dir


@router.get("/replay/timeline")
async def replay_timeline(request: Request, scenario: str = Query(...)) -> dict:
    """Ham olay dökümü + hat tanımı (canlı hat şeridi). İş kuralı YOK; frontend
    indirgeyici tüketir. FIREWALL: ground_truth alınmaz; stream ile aynı izolasyon
    (in-memory DuckDB, paylaşılan repo'ya dokunulmaz)."""
    cfg, data_dir = _resolve_scenario_dir(request, scenario)

    def build() -> dict:
        temp = DuckDBRepository(":memory:")
        temp.connect()
        try:
            temp.init_schema()
            load_csv_dir(data_dir, temp)
            events = temp.fetch_events(None, None)
        finally:
            temp.close()
        line = load_line_definition(cfg.line_config_path)
        evs = sorted(events, key=lambda e: str(e["timestamp"]))
        return {
            "line": [{"id": t.id, "name": t.name} for t in line.tanks],
            "events": [
                {
                    "timestamp": str(e["timestamp"]),
                    "carrier_id": e.get("carrier_id") or None,
                    "station_id": e.get("station_id") or None,
                    "event_type": e["event_type"],
                    "duration": float(e["duration"]),
                    "reason_code": e.get("reason_code") or None,
                }
                for e in evs
            ],
        }

    return await asyncio.to_thread(build)
```

`replay_stream` gövdesindeki eski 8 satırlık çözüm bloğu silinir; davranış birebir aynı kalır (mevcut `test_replay_stream.py` bunu doğrular).

- [ ] **Step 4: Testler + tam süit**

Run: `cd backend && pytest tests/test_replay_timeline.py tests/test_replay_stream.py -q` sonra `cd backend && pytest -q`
Expected: tümü PASS (refactor stream testlerini bozmamalı).

- [ ] **Step 5: Lint + commit**

Run: `cd backend && ruff check .` → temiz.

```bash
git add backend/app/api/replay_routes.py backend/tests/test_replay_timeline.py
git commit -m "feat(replay): GET /replay/timeline — hat tanımı + ham olay dökümü

Canlı hat animasyonunun veri beslemesi; stream ile ortak senaryo çözümü
helper'a çıktı, izolasyon deseni aynı.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Frontend — durum-indirgeyici `replayLine.ts`

**Files:**
- Modify: `frontend/src/api/types.ts` (dosya sonuna `TimelineEvent`/`ReplayTimeline`)
- Create: `frontend/src/replay/replayLine.ts`
- Test: `frontend/src/replay/replayLine.test.ts` (yeni)

**Interfaces:**
- Consumes: Task 1'in JSON şeması.
- Produces (Task 4 kullanır): `tsMs(s: string): number`; `buildTimeline(payload: ReplayTimeline): Timeline`;
  `lineStateAt(tl: Timeline, tMs: number): LineState`; sabitler `YUKLEME`, `CIKIS`; tipler
  `CarrierPos` (`tankta|tasiniyor|bekliyor|strip|cikti`), `CarrierState {id, pos, redo}`,
  `TankState {id, name, durum: bos|isliyor|bekliyor|mikro|durus, carrier?, reason?}`,
  `HoistState {durum: bos|tasiyor|durus, carrier?, from?, to?, progress?, reason?}`,
  `LineState {tanks, hoist, carriers, yuklenen, cikan, redo}`.

- [ ] **Step 1: types.ts'e API tipleri**

`frontend/src/api/types.ts` dosya sonuna:

```ts
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
```

- [ ] **Step 2: Failing testler**

Create `frontend/src/replay/replayLine.test.ts`:

```ts
import { describe, expect, it } from 'vitest'

import type { ReplayTimeline, TimelineEvent } from '../api/types'
import { CIKIS, YUKLEME, buildTimeline, lineStateAt, tsMs } from './replayLine'

// Kurgu hat: 2 tank. Zaman eksenini okunur tutmak için dakika ofsetli damga üretici.
const T0 = Date.parse('2026-01-05T06:00:00.000')
const at = (min: number): string =>
  new Date(T0 + min * 60_000).toISOString().slice(0, 23).replace('T', ' ')
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
```

- [ ] **Step 3: Testlerin başarısız olduğunu gör**

Run: `cd frontend && npm run test`
Expected: FAIL — `./replayLine` modülü yok.

- [ ] **Step 4: Implementasyon**

Create `frontend/src/replay/replayLine.ts`:

```ts
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

/** Backend "YYYY-MM-DD HH:MM:SS.sss" → epoch ms (tüm damgalar aynı biçim/saat dilimi). */
export const tsMs = (s: string): number => new Date(s.replace(' ', 'T')).getTime()

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
```

- [ ] **Step 5: Testler geçer + zincir**

Run: `cd frontend && npm run test` → tümü PASS. Sonra `npm run build && npm run lint` → temiz.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/replay/replayLine.ts frontend/src/replay/replayLine.test.ts
git commit -m "feat(replay): hat durum-indirgeyicisi — lineStateAt (saf, olay dökümünden)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Frontend — sanal saat `useVirtualClock.ts`

**Files:**
- Create: `frontend/src/replay/useVirtualClock.ts`
- Test: `frontend/src/replay/useVirtualClock.test.ts` (yeni)

**Interfaces:**
- Produces (Task 4 kullanır): `interpolate(prev, target, elapsedMs, tickMs): number` (saf);
  `useVirtualClock(targetMs: number | null, tickMs: number): number | null` (rAF hook;
  target null → saat null; yeni target gelince mevcut konumdan yeni hedefe lineer akar).

- [ ] **Step 1: Failing test**

Create `frontend/src/replay/useVirtualClock.test.ts`:

```ts
import { describe, expect, it } from 'vitest'

import { interpolate } from './useVirtualClock'

describe('interpolate — sanal saat lineer yaklaşım', () => {
  it('elapsed=0 → prev; elapsed≥tick → target; yarıda → orta', () => {
    expect(interpolate(100, 200, 0, 200)).toBe(100)
    expect(interpolate(100, 200, 200, 200)).toBe(200)
    expect(interpolate(100, 200, 300, 200)).toBe(200) // taşma kıskacı
    expect(interpolate(100, 200, 100, 200)).toBe(150)
  })

  it('tickMs=0 → doğrudan hedef (bölme koruması)', () => {
    expect(interpolate(100, 200, 50, 0)).toBe(200)
  })
})
```

- [ ] **Step 2: Fail gör** — `cd frontend && npm run test` → modül yok.

- [ ] **Step 3: Implementasyon**

Create `frontend/src/replay/useVirtualClock.ts`:

```ts
// SSE snapshot hedefine (to damgası) lineer yaklaşan sanal saat. Hedefler ~tickMs
// arayla gelir (200/speed ms); saat iki hedef arasında rAF ile akar → şerit 60fps,
// SSE şeması değişmez. rAF yalnız bu hook'u kullanan bileşeni yeniden çizer.
import { useEffect, useRef, useState } from 'react'

/** prev'den target'a, tickMs içinde lineer; elapsed kıskaçlı. Saf — testli. */
export const interpolate = (
  prev: number,
  target: number,
  elapsedMs: number,
  tickMs: number,
): number =>
  prev + (target - prev) * (tickMs > 0 ? Math.max(0, Math.min(1, elapsedMs / tickMs)) : 1)

export function useVirtualClock(targetMs: number | null, tickMs: number): number | null {
  const [clock, setClock] = useState<number | null>(null)
  const ref = useRef<{ prev: number; target: number; setAt: number } | null>(null)

  // Yeni hedef: mevcut saat konumundan yeni hedefe akmaya başla (sıçrama yok).
  useEffect(() => {
    if (targetMs == null) {
      ref.current = null
      setClock(null)
      return
    }
    const now = performance.now()
    const cur = ref.current
    const from = cur ? interpolate(cur.prev, cur.target, now - cur.setAt, tickMs) : targetMs
    ref.current = { prev: from, target: targetMs, setAt: now }
    setClock(from)
  }, [targetMs, tickMs])

  // rAF döngüsü: hedef varken her karede saat ilerler; unmount'ta temizlenir.
  const active = targetMs != null
  useEffect(() => {
    if (!active) return
    let raf = 0
    const loop = () => {
      const s = ref.current
      if (s) setClock(interpolate(s.prev, s.target, performance.now() - s.setAt, tickMs))
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [active, tickMs])

  return clock
}
```

- [ ] **Step 4: Testler geçer** — `cd frontend && npm run test` → PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/replay/useVirtualClock.ts frontend/src/replay/useVirtualClock.test.ts
git commit -m "feat(replay): sanal saat hook'u — SSE hedefine rAF lineer yaklaşım

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Frontend — `LineStrip` SVG bileşeni + Replay entegrasyonu

**Files:**
- Modify: `frontend/src/styles/theme.ts` (REASON_LABEL; `catLabel` bloğunun yanına)
- Modify: `frontend/src/api/client.ts` (`api.replayTimeline`)
- Create: `frontend/src/components/LineStrip.tsx`
- Modify: `frontend/src/styles/theme.css` (dosya sonuna `.ls-*` blok)
- Modify: `frontend/src/views/Replay.tsx` (timeline sorgusu + "Canlı Hat" bölgesi)
- Test: `frontend/src/components/LineStrip.test.tsx` (yeni)

**Interfaces:**
- Consumes: Task 2 (`buildTimeline`, `lineStateAt`, `tsMs`, `YUKLEME`, `CIKIS`), Task 3
  (`useVirtualClock`), Task 1 JSON'u, `Card` (`{eyebrow, className?, children}`).
- Produces: `LineStrip({ timeline: ReplayTimeline | null, targetTo: string | null, tickMs: number, running: boolean })`;
  `api.replayTimeline(scenario: string): Promise<ReplayTimeline>`; `reasonLabel(code: string): string`.

- [ ] **Step 1: Failing testler**

Create `frontend/src/components/LineStrip.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { ReplayTimeline } from '../api/types'
import LineStrip from './LineStrip'

const LINE = [
  { id: 'tankA', name: 'Tank A' },
  { id: 'tankB', name: 'Tank B' },
]
const TL: ReplayTimeline = {
  line: LINE,
  events: [
    { timestamp: '2026-01-05 06:00:00.000', carrier_id: 'CAR-0001', station_id: null, event_type: 'LOAD', duration: 0, reason_code: null },
    { timestamp: '2026-01-05 06:00:00.000', carrier_id: 'CAR-0001', station_id: 'HOIST', event_type: 'MOVE', duration: 0.5, reason_code: null },
    { timestamp: '2026-01-05 06:00:30.000', carrier_id: 'CAR-0001', station_id: 'tankA', event_type: 'PROCESS', duration: 5, reason_code: null },
    { timestamp: '2026-01-05 06:01:00.000', carrier_id: null, station_id: 'tankB', event_type: 'DOWNTIME', duration: 10, reason_code: 'rectifier_ariza' },
  ],
}

describe('LineStrip', () => {
  it('timeline yokken bekleme metni gösterir', () => {
    render(<LineStrip timeline={null} targetTo={null} tickMs={200} running={false} />)
    expect(screen.getByText(/Oynat/)).toBeInTheDocument()
  })

  it('duruştaki tank kırmızı sınıf + Türkçe neden etiketi alır', () => {
    render(
      <LineStrip timeline={TL} targetTo="2026-01-05 06:02:00.000" tickMs={200} running={true} />,
    )
    expect(screen.getByText('Redresör arızası')).toBeInTheDocument()
    expect(document.querySelector('.ls-tank-durus')).not.toBeNull()
    // Tank adları uçtan gelir, gömülü değil:
    expect(screen.getByText('Tank A')).toBeInTheDocument()
  })

  it('sayaçları gösterir (yüklenen/çıkan/redo)', () => {
    render(
      <LineStrip timeline={TL} targetTo="2026-01-05 06:02:00.000" tickMs={200} running={true} />,
    )
    expect(screen.getByText('Yüklenen')).toBeInTheDocument()
    expect(screen.getByText('Redo')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Fail gör** — `cd frontend && npm run test` → LineStrip yok.

- [ ] **Step 3: Implementasyon (5 dosya)**

(a) `frontend/src/styles/theme.ts` — `catLabel` tanımından sonra:

```ts
// Duruş neden kodu → Türkçe etiket (canlı hat şeridi). CATEGORY_LABEL deseniyle aynı;
// backend ham kod döndürür, jargon kullanıcıya gösterilmez. Bilinmeyen kodda ham koda düş.
export const REASON_LABEL: Record<string, string> = {
  hoist_ariza: 'Vinç arızası',
  rectifier_ariza: 'Redresör arızası',
  furnace_ariza: 'Fırın arızası',
}
export const reasonLabel = (code: string): string => REASON_LABEL[code] ?? code
```

(b) `frontend/src/api/client.ts` — import'a `ReplayTimeline` ekle; `api` objesine
(`scenarios` satırından sonra):

```ts
  replayTimeline: (scenario: string) =>
    getJSON<ReplayTimeline>(`/replay/timeline?scenario=${encodeURIComponent(scenario)}`),
```

(c) Create `frontend/src/components/LineStrip.tsx`:

```tsx
// Canlı hat şeridi: tanklar (banyo kapları) + vinç rayı + askı çipleri, SSE sanal
// saatine senkron SVG. rAF yeniden-çizimi YALNIZ bu bileşendedir (Chart.js kartları
// etkilenmez). Foundry Gauge: keskin köşe, hairline, tabular-nums, glow yok.
import { useMemo } from 'react'

import type { ReplayTimeline } from '../api/types'
import {
  CIKIS,
  YUKLEME,
  buildTimeline,
  lineStateAt,
  tsMs,
  type CarrierState,
} from '../replay/replayLine'
import { useVirtualClock } from '../replay/useVirtualClock'
import { reasonLabel } from '../styles/theme'
import Card from './Card'

interface Props {
  timeline: ReplayTimeline | null
  targetTo: string | null // son SSE snapshot'ının `to` damgası
  tickMs: number // snapshot'lar arası gerçek süre (200/speed)
  running: boolean
}

// SVG geometrisi (viewBox birimleri; 7 tanka göre ölçülü, tank sayısına uyarlanır).
const CAP_W = 78 // uç kapak genişliği
const TANK_W = 118
const TANK_GAP = 12
const H = 176
const RAIL_Y = 26
const VESSEL_Y = 62
const VESSEL_H = 66
const CHIP_W = 40
const CHIP_H = 22

export default function LineStrip({ timeline, targetTo, tickMs, running }: Props) {
  const tl = useMemo(() => (timeline ? buildTimeline(timeline) : null), [timeline])
  const clock = useVirtualClock(targetTo ? tsMs(targetTo) : null, tickMs)

  if (!tl || clock == null) {
    return (
      <Card eyebrow="Canlı Hat" className="card-wide ls-card">
        <p className="muted">
          Oynat'a basın — hat canlanacak: askılar tanklarda ilerler, duruşlar kızarır,
          redo askıları geri döner.
        </p>
      </Card>
    )
  }

  const state = lineStateAt(tl, clock)
  const n = state.tanks.length
  const W = CAP_W * 2 + 40 + n * (TANK_W + TANK_GAP)
  const tankX = (i: number) => CAP_W + 20 + i * (TANK_W + TANK_GAP)
  const idxOf = new Map(state.tanks.map((t, i) => [t.id, i]))
  // İstasyon → çip merkez x'i (pseudo-istasyonlar uç kapaklara düşer).
  const cx = (station: string): number => {
    if (station === YUKLEME) return CAP_W / 2 + 4
    if (station === CIKIS) return W - CAP_W / 2 - 4
    const i = idxOf.get(station) ?? 0
    return tankX(i) + TANK_W / 2
  }

  const clockLabel = new Date(clock).toLocaleTimeString('tr-TR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

  const chip = (c: CarrierState) => {
    const p = c.pos
    let x = 0
    let y = 0
    if (p.kind === 'tankta' || p.kind === 'bekliyor') {
      x = cx(p.station)
      y = VESSEL_Y + 32
    } else if (p.kind === 'tasiniyor') {
      x = cx(p.from) + (cx(p.to) - cx(p.from)) * p.progress
      y = RAIL_Y + 8
    } else if (p.kind === 'strip') {
      // Söküm/geri dönüş: çıkıştan yüklemeye, alttaki kesikli dönüş yolunda.
      x = cx(CIKIS) + (cx(YUKLEME) - cx(CIKIS)) * p.progress
      y = H - 14
    } else {
      return null
    }
    const cls = `ls-chip${c.redo ? ' ls-chip-redo' : ''}${p.kind === 'bekliyor' ? ' ls-chip-bekliyor' : ''}`
    return (
      <g key={c.id} className={cls} transform={`translate(${x}, ${y})`}>
        <rect x={-CHIP_W / 2} y={-CHIP_H / 2} width={CHIP_W} height={CHIP_H} rx={2} />
        <text y={4}>{c.id.slice(-4)}</text>
      </g>
    )
  }

  return (
    <Card eyebrow="Canlı Hat" className="card-wide ls-card">
      <div className="ls-head">
        <span className="ls-clock" aria-label="Sanal saat">
          {clockLabel}
        </span>
        <div className="ls-counters">
          <span>
            Yüklenen <strong>{state.yuklenen}</strong>
          </span>
          <span>
            Çıkan <strong>{state.cikan}</strong>
          </span>
          <span className="ls-cnt-redo">
            Redo <strong>{state.redo}</strong>
          </span>
        </div>
      </div>
      <div className="ls-scroll">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className={`ls-svg${running ? '' : ' ls-paused'}`}
          role="img"
          aria-label="Canlı hat şeridi"
        >
          {/* Vinç rayı */}
          <line className="ls-rail" x1={cx(YUKLEME)} y1={RAIL_Y} x2={cx(CIKIS)} y2={RAIL_Y} />
          {state.hoist.durum === 'durus' && (
            <text className="ls-reason ls-hoist-reason" x={W / 2} y={RAIL_Y - 10}>
              {reasonLabel(state.hoist.reason ?? '')}
            </text>
          )}
          {/* Uç kapaklar */}
          <g className="ls-cap" transform={`translate(4, ${VESSEL_Y})`}>
            <rect width={CAP_W} height={VESSEL_H} />
            <text x={CAP_W / 2} y={VESSEL_H / 2 + 4}>
              Yükleme →
            </text>
          </g>
          <g className="ls-cap" transform={`translate(${W - CAP_W - 4}, ${VESSEL_Y})`}>
            <rect width={CAP_W} height={VESSEL_H} />
            <text x={CAP_W / 2} y={VESSEL_H / 2 + 4}>
              → QC / Çıkış
            </text>
          </g>
          {/* Dönüş yolu (redo) — kesikli */}
          <line
            className="ls-return"
            x1={cx(CIKIS)}
            y1={H - 14}
            x2={cx(YUKLEME)}
            y2={H - 14}
          />
          {/* Tanklar */}
          {state.tanks.map((tk, i) => (
            <g key={tk.id} transform={`translate(${tankX(i)}, 0)`}>
              <g
                className={`ls-tank ls-tank-${tk.durum}${tk.durum === 'mikro' ? ' ls-flash' : ''}`}
              >
                <rect className="ls-vessel" x={0} y={VESSEL_Y} width={TANK_W} height={VESSEL_H} />
                <rect
                  className="ls-liquid"
                  x={4}
                  y={VESSEL_Y + 22}
                  width={TANK_W - 8}
                  height={VESSEL_H - 26}
                />
              </g>
              {tk.durum === 'durus' && tk.reason && (
                <text className="ls-reason" x={TANK_W / 2} y={VESSEL_Y - 8}>
                  {reasonLabel(tk.reason)}
                </text>
              )}
              <text className="ls-tankname" x={TANK_W / 2} y={VESSEL_Y + VESSEL_H + 18}>
                {tk.name}
              </text>
            </g>
          ))}
          {/* Vinç troleyi */}
          {state.hoist.durum === 'tasiyor' && state.hoist.from && state.hoist.to && (
            <rect
              className="ls-trolley"
              x={
                cx(state.hoist.from) +
                (cx(state.hoist.to) - cx(state.hoist.from)) * (state.hoist.progress ?? 0) -
                10
              }
              y={RAIL_Y - 5}
              width={20}
              height={10}
            />
          )}
          {state.hoist.durum === 'durus' && (
            <rect className="ls-trolley ls-trolley-durus" x={W / 2 - 10} y={RAIL_Y - 5} width={20} height={10} />
          )}
          {/* Askı çipleri */}
          {state.carriers.map(chip)}
        </svg>
      </div>
    </Card>
  )
}
```

(d) `frontend/src/styles/theme.css` — dosya sonuna:

```css
/* ── Canlı Hat şeridi (Replay): tanklar, vinç rayı, askı çipleri ── */
.ls-head {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 0.5rem;
}
.ls-clock {
  font-family: var(--mono); font-variant-numeric: tabular-nums;
  font-size: 0.85rem; color: var(--ink);
  border: 1px solid var(--line); padding: 2px 8px; background: var(--surface-inset);
}
.ls-counters { display: flex; gap: 14px; font-size: 0.85rem; color: var(--muted); }
.ls-counters strong {
  color: var(--ink); font-family: var(--mono); font-variant-numeric: tabular-nums;
}
.ls-cnt-redo strong { color: #a8443a; }
.ls-scroll { overflow-x: auto; }
.ls-svg { display: block; width: 100%; min-width: 900px; height: auto; }
.ls-paused { opacity: 0.85; }
.ls-rail { stroke: var(--line-strong, #cdd4dc); stroke-width: 2; }
.ls-return { stroke: #a8443a; stroke-width: 1; stroke-dasharray: 4 4; opacity: 0.45; }
.ls-cap rect { fill: var(--surface-inset); stroke: var(--line); }
.ls-cap text, .ls-tankname {
  font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  fill: var(--muted); text-anchor: middle;
}
.ls-vessel { fill: var(--surface); stroke: var(--line-strong, #cdd4dc); }
.ls-liquid { fill: var(--steel); transition: fill 150ms linear; }
.ls-tank-isliyor .ls-liquid { fill: #dbe7f4; } /* accent-soft tonu: işlem sürüyor */
.ls-tank-bekliyor .ls-liquid { fill: #f2e8d5; } /* threshold-amber tonu: vinç bekleniyor */
.ls-tank-durus .ls-vessel { stroke: #a8443a; }
.ls-tank-durus .ls-liquid { fill: #f0dcd9; }
.ls-reason {
  font-size: 10px; font-weight: 700; fill: #a8443a; text-anchor: middle;
  letter-spacing: 0.04em;
}
.ls-flash { animation: lsFlash 0.6s ease-in-out infinite alternate; }
@keyframes lsFlash { from { opacity: 1; } to { opacity: 0.55; } }
.ls-trolley { fill: var(--ink); }
.ls-trolley-durus { fill: #a8443a; }
.ls-chip rect { fill: var(--ink); }
.ls-chip text {
  font-family: var(--mono); font-size: 9px; fill: #fff; text-anchor: middle;
  font-variant-numeric: tabular-nums;
}
.ls-chip-bekliyor rect { stroke: #b5832f; stroke-width: 1.5; }
.ls-chip-redo rect { fill: #a8443a; }
@media (max-width: 768px) {
  .ls-head { flex-direction: column; gap: 6px; align-items: flex-start; }
}
```

(e) `frontend/src/views/Replay.tsx` — üç ekleme:

İmport bloğuna (`Card` satırından sonra, alfabetik): `import LineStrip from '../components/LineStrip'`.

`catalogLoading` sorgusunun altına:

```tsx
  const timelineQ = useQuery({
    queryKey: ['replay-timeline', scenario],
    queryFn: () => api.replayTimeline(scenario),
    staleTime: Infinity,
  })
```

`<main className="grid">` içinde, `<div className="zone-head">Canlı Durum</div>` satırının ÜSTÜNE:

```tsx
        <div className="zone-head">Canlı Hat</div>
        <LineStrip
          timeline={timelineQ.data ?? null}
          targetTo={snap?.to ?? null}
          tickMs={200 / speed}
          running={running}
        />
```

- [ ] **Step 4: Testler + zincir**

Run: `cd frontend && npm run test` → tümü PASS (LineStrip 3 + önceki).
Run: `cd frontend && npm run build && npm run lint` → temiz.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles/theme.ts frontend/src/api/client.ts frontend/src/components/LineStrip.tsx frontend/src/components/LineStrip.test.tsx frontend/src/styles/theme.css frontend/src/views/Replay.tsx
git commit -m "feat(replay): LineStrip — canlı hat şeridi (SVG) + Replay entegrasyonu

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Görsel cila turu (spec'in kalite çıtası — ZORUNLU)

**Files:**
- Modify: `frontend/src/components/LineStrip.tsx` ve/veya `frontend/src/styles/theme.css` (bulgulara göre)
- Output: `.superpowers/sdd/ls-normal.png`, `.superpowers/sdd/ls-durus.png`, `.superpowers/sdd/ls-redo.png` (git'e girmez)

**Interfaces:**
- Consumes: Task 1–4'ün tamamı (çalışan uygulama).
- Produces: kabul ölçütlerini karşılayan son görsel + 3 ekran görüntüsü (PR gövdesi/kullanıcı onayı için).

- [ ] **Step 1: Uygulamayı yerel başlat**

`make clean` (bayat .duckdb tuzağı) → `make frontend-sync` (dist güncelle; COMMIT YOK) →
`cd backend && uvicorn app.main:app --port 8010` (arka plan; 8000 Docker'da olabilir).

- [ ] **Step 2: Üç kritik anın ekran görüntüsü**

Playwright MCP araçlarıyla `http://localhost:8010` → Replay sekmesi:
1. **Normal akış** (`baseline`, hız ×1): çipler tanklarda/rayda → `ls-normal.png`
2. **Duruş anı** (`breakdown_storm`, hız ×5): kırmızı tank + Türkçe neden etiketi görünürken → `ls-durus.png`
3. **Redo dönüşü** (`redo_crisis`, hız ×5): mercan çip dönüş yolundayken + Redo sayacı > 0 → `ls-redo.png`

- [ ] **Step 3: Kabul ölçütlerine karşı denetle ve düzelt**

Spec ölçütleri tek tek: (1) 1280px'te tek satır, tank adları kısaltılmasız ve taşmasız;
(2) çip hareketi akıcı (görsel olarak sıçramasız); (3) duruş kırmızısı ↔ redo mercanı
ayırt edilir (duruş = kap kenarı+sıvı, redo = çip dolgusu — karışıyorsa tonu ayarla);
(4) 768px'te `.ls-scroll` yatay kaydırıyor, gövde taşmıyor; (5) hiza/boşluk Foundry
Gauge kartlarıyla uyumlu (eyebrow, hairline, boşluk ritmi). Bulunan her sorunda
geometri sabitlerini/CSS'i düzelt, sayfayı yenile, YENİDEN görüntü al — ölçüt
karşılanana dek döngü. Her düzeltmeden sonra `cd frontend && npm run test` yeşil kalmalı.

- [ ] **Step 4: Süreci kapat, commit**

uvicorn'u durdur.

```bash
git add frontend/src/components/LineStrip.tsx frontend/src/styles/theme.css
git commit -m "polish(replay): hat şeridi görsel cila — kabul ölçütleri turu

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

(Değişiklik çıkmadıysa commit atlanır; ekran görüntüleri raporda kalır.)

---

### Task 6: Uçtan uca doğrulama + PR

**Files:** (yalnız doğrulama; kod değişikliği beklenmez)

**Interfaces:**
- Consumes: Task 1–5.
- Produces: merge'e hazır branch + PR.

- [ ] **Step 1: Tam süitler**

Run: `make ci` → ruff + pytest tümü PASS. `cd frontend && npm run test` → tümü PASS.
`cd frontend && npm run build && npm run lint` → temiz.

- [ ] **Step 2: Uçtan uca göz kontrolü**

`make clean` → `make frontend-sync` → uvicorn (8010, arka plan) → Replay'de `breakdown_storm`
oynat: şerit SSE ile senkron ilerliyor (sanal saat kartlardaki ilerlemeyle tutarlı),
Duraklat'ta şerit donuyor, hız ×5'te akış hızlanıyor, `curl -s "localhost:8010/replay/timeline?scenario=baseline" | head -c 300`
beklenen JSON. uvicorn'u kapat. `frontend_dist` COMMIT EDİLMEZ.

- [ ] **Step 3: Push + PR**

```bash
git push -u origin feat/hat-animasyonu
```

`gh pr create` — başlık: `Canlı hat animasyonu (Replay) — tank şeridi + askı akışı`;
gövde: spec linki, mimari özet (timeline ucu + saf indirgeyici + sanal saat + SVG),
test sayıları, 3 ekran görüntüsünün varlığına atıf (yerelde `.superpowers/sdd/ls-*.png`),
görsel kabul ölçütleri karşılandı notu. Gövde şu satırla biter:
`🤖 Generated with [Claude Code](https://claude.com/claude-code)`

---

## Self-Review Notu

- **Spec kapsaması:** timeline ucu+izolasyon (T1), indirgeyici tüm konum türleri+öncelik+sayaçlar+kıskaç (T2), sanal saat lineer+rAF temizliği (T3), SVG şerit+Türkçe nedenler+uç kapaklar+dönüş yolu+Replay yerleşimi (T4), görsel çıta+3 an (T5), zincir+PR (T6). "EventSource düşerse gri beklemede": `running=false` → `.ls-paused` opaklığı bunu karşılar (stop() zaten onerror'da çağrılıyor).
- **Tip tutarlılığı:** `ReplayTimeline/TimelineEvent` types.ts'te (T2 üretir, T4 tüketir); `lineStateAt/buildTimeline/tsMs/YUKLEME/CIKIS` imzaları T2↔T4 birebir; `interpolate/useVirtualClock` T3↔T4 birebir; `reasonLabel` T4 içinde tanımlı+tüketimli.
- **Plan tuzağı düzeltmesi:** önceki planın "dist commit" hatası burada YOK — `frontend_dist` gitignore'da, yalnız yerel sync.
- **rAF izolasyonu:** saat hook'u LineStrip İÇİNDE — Replay/Chart.js kartları kare başına yeniden çizilmez.

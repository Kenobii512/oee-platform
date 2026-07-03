# Vardiya Künyesi Kartı Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/oee` yanıtına vardiya bağlam alanlarını (yüklenen/iyi/redo parça sayıları + gözlem penceresi) ekleyip pano Detay görünümüne "Vardiya Künyesi" kartını koymak.

**Architecture:** Backend zaten `_quality_metrics` içinde parça toplamlarını ve `availability_from_events` içinde pencere süresini hesaplıyor; `OeeResult` dataclass'ına default'lu 4 alan eklenir, `/oee` `asdict` ile otomatik döndürür. Frontend'te yeni `ShiftSummary` bileşeni bu alanları okur; alanlar yoksa/`loaded_qty<=0` ise render etmez. Formül çoğaltılmaz (tek istisna: "İyi (ilk geçiş)" = `loaded − redo`, Q'nun payıyla birebir).

**Tech Stack:** FastAPI + dataclasses (backend), React + TypeScript + vitest (frontend), Foundry Gauge CSS dili (`theme.css` hairline/tabular-nums desenleri).

**Spec:** `docs/superpowers/specs/2026-07-03-vardiya-kunyesi-design.md`

## Global Constraints

- Branch: `feat/vardiya-kunyesi` (açık, spec commit'li `98ba711`).
- Kartta kullanım oranı ve duruş dökümü GÖSTERİLMEZ (spec "yalın" varyant onaylı).
- `good_count` yanıtta bulunur ama kartta gösterilmez (no-scrap'te ≈ yüklenen).
- `downtime_union_min` yanıta EKLENMEZ (YAGNI).
- Trend/Replay kendi dict'lerini kurar — bu iş onlara DOKUNMAZ.
- Kart yalnız Detay görünümünde: hem `{detay && ...}` koşulu hem `Card period` (Amir/Özet gizleme deseni, `DataQualityDetail` ile aynı).
- Tüm metinler Türkçe; sayılar `tr-TR` biçiminde (binlik ayraç ".", ondalık ",").
- Commit mesajı gövdesi şu satırla biter: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: Backend — OeeResult bağlam alanları + endpoint testi

**Files:**
- Modify: `backend/app/analytics/oee.py` (OeeResult ~satır 28–37, `_quality_metrics` ~satır 110–122, `compute_oee` ~satır 125–149)
- Test: `backend/tests/test_oee_endpoint.py`

**Interfaces:**
- Consumes: mevcut `availability_from_events(events) -> (avail, span, downtime_union)`.
- Produces: `/oee` JSON gövdesinde yeni anahtarlar `loaded_qty: float`, `good_count: float`, `redo_count: float`, `span_min: float` (Task 2 frontend bunları okur). `_quality_metrics(production) -> tuple[float, float, float, float, float]` = `(first_pass, final_yield, loaded, redo, good)`.

- [ ] **Step 1: Failing test — endpoint testine alan + tutarlılık doğrulaması ekle**

`backend/tests/test_oee_endpoint.py` içinde `test_oee_endpoint`'in sonuna (satır 21'deki `final_yield` assert'inden sonra, aynı girinti düzeyinde) ekle:

```python
        # Vardiya künyesi bağlam alanları (spec 2026-07-03): sayılar + pencere.
        assert set(body) >= {"loaded_qty", "good_count", "redo_count", "span_min"}
        assert body["loaded_qty"] > 0 and body["span_min"] > 0
        # Q = first_pass = (loaded - redo) / loaded — kart "İyi (ilk geçiş)" bununla tutarlı.
        first_pass = (body["loaded_qty"] - body["redo_count"]) / body["loaded_qty"]
        assert abs(body["quality"] - first_pass) < 1e-9
```

- [ ] **Step 2: Testin başarısız olduğunu gör**

Run: `cd backend && pytest tests/test_oee_endpoint.py -q`
Expected: FAIL — `assert set(body) >= {...}` satırında (yeni anahtarlar yanıtta yok).

- [ ] **Step 3: Minimal implementasyon**

`backend/app/analytics/oee.py` — üç değişiklik:

(a) `OeeResult`'a default'lu alanlar (mevcut `final_yield` satırından SONRA):

```python
@dataclass(frozen=True)
class OeeResult:
    availability: float
    performance: float
    quality: float       # ilk-geçiş kalite (first_pass) — OEE'nin Q'su
    oee: float
    utilization: float
    planned_downtime_min: float
    final_yield: float = 1.0  # Σ good / Σ loaded (no-scrap → ≈%100)
    # Vardiya künyesi bağlamı: ham toplamlar + gözlem penceresi (dk).
    loaded_qty: float = 0.0
    good_count: float = 0.0
    redo_count: float = 0.0
    span_min: float = 0.0
```

(b) `_quality_metrics` toplamları da döndürür (tek çağıran `compute_oee`; toplamlar iki kez hesaplanmasın):

```python
def _quality_metrics(production: list[dict]) -> tuple[float, float, float, float, float]:
    """(first_pass, final_yield, loaded, redo, good) döndürür (no-scrap modeli).

    first_pass = (Σ loaded − Σ redo) / Σ loaded → ilk geçişte iyi oranı (OEE'nin Q'su;
    redo'dan geçen parça cezalandırılır). final_yield = Σ good / Σ loaded → nihai verim
    (no-scrap → ≈%100). Doluluk kaybı Q'da değil; ayrı FILL_LOSS kanalındadır.
    Ham toplamlar vardiya künyesi için yüzeye çıkar (OeeResult bağlam alanları).
    """
    loaded = sum(p["loaded_qty"] for p in production)
    redo = sum(p["redo_count"] for p in production)
    good = sum(p["good_count"] for p in production)
    if loaded <= 0:
        return 0.0, 0.0, loaded, redo, good
    return _clamp01((loaded - redo) / loaded), _clamp01(good / loaded), loaded, redo, good
```

(c) `compute_oee` gövdesinde çağrıyı ve dönüşü güncelle (fonksiyonun geri kalanı aynen kalır):

```python
    avail, span, _dt = availability_from_events(events)
    perf = _performance(events, len(production), line)
    qual, final_yield, loaded, redo, good = _quality_metrics(production)
    oee = avail * perf * qual
    operating = span * avail
    if calendar_min is not None and calendar_min > 0:
        utilization = _clamp01(operating / calendar_min)
    else:
        calendar = span + planned_downtime_min
        utilization = _clamp01(operating / calendar) if calendar > 0 else 0.0
    return OeeResult(
        avail, perf, qual, oee, utilization, planned_downtime_min, final_yield,
        loaded_qty=float(loaded), good_count=float(good), redo_count=float(redo),
        span_min=float(span),
    )
```

Not: boş-veri erken dönüşü (`if not events or not production:` satırı) DEĞİŞMEZ — yeni alanlar default 0.0 alır.

- [ ] **Step 4: Testlerin geçtiğini gör (tam backend süiti)**

Run: `cd backend && pytest -q`
Expected: tümü PASS (279 mevcut + genişletilmiş endpoint testi; başka test `OeeResult`'ı pozisyonel kurmadığından kırılma beklenmez — kırılırsa default'lu alan sıralamasını kontrol et).

- [ ] **Step 5: Lint + commit**

Run: `cd backend && ruff check .`
Expected: hatasız.

```bash
git add backend/app/analytics/oee.py backend/tests/test_oee_endpoint.py
git commit -m "feat(oee): /oee yanıtına vardiya bağlam alanları (loaded/good/redo/span)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Frontend — ShiftSummary kartı + biçim yardımcıları

**Files:**
- Modify: `frontend/src/api/types.ts` (Oee arayüzü, ~satır 6–15)
- Modify: `frontend/src/styles/theme.ts` (yardımcılar; `num1`/`pct`/`tl`'nin yanına)
- Create: `frontend/src/components/ShiftSummary.tsx`
- Modify: `frontend/src/styles/theme.css` (dosya sonuna `.kn-*` blok)
- Modify: `frontend/src/views/Dashboard.tsx` (~satır 131–132 civarı, TrendChart'tan sonra)
- Test: `frontend/src/components/components.test.tsx`

**Interfaces:**
- Consumes: `Oee` tipindeki yeni opsiyonel alanlar (Task 1'in JSON anahtarları): `loaded_qty?`, `good_count?`, `redo_count?`, `span_min?`.
- Produces: `ShiftSummary({ oee: Oee })` bileşeni (alan eksik/`loaded_qty<=0` → `null` döner); `theme.ts`'te `num0(x: number): string` (tam sayı tr biçimi) ve `hm(min: number): string` (süre etiketi).

- [ ] **Step 1: Failing testler — components.test.tsx'e ShiftSummary + hm testleri ekle**

`frontend/src/components/components.test.tsx` — import bloğuna ekle:

```tsx
import { catLabel, hm } from '../styles/theme'
import ShiftSummary from './ShiftSummary'
```

(mevcut `import { catLabel } ...` satırını yukarıdaki gibi genişlet). Dosyanın sonuna ekle:

```tsx
describe('ShiftSummary (Vardiya Künyesi)', () => {
  const FULL: Oee = { ...OEE, loaded_qty: 1240, good_count: 1240, redo_count: 72, span_min: 480 }

  it('pencere + sayıları gösterir; ilk geçiş = yüklenen − redo', () => {
    render(<ShiftSummary oee={FULL} />)
    expect(screen.getByText('Vardiya Künyesi')).toBeInTheDocument()
    expect(screen.getByText('8 s 00 dk')).toBeInTheDocument()
    expect(screen.getByText('1.240 parça')).toBeInTheDocument() // yüklenen
    expect(screen.getByText('1.168 parça')).toBeInTheDocument() // ilk geçiş = 1240−72
    expect(screen.getByText('72 parça')).toBeInTheDocument() // redo
  })

  it('bağlam alanları yokken hiç render olmaz (eski yanıt uyumu)', () => {
    const { container } = render(<ShiftSummary oee={OEE} />)
    expect(container.firstChild).toBeNull()
  })

  it('loaded_qty=0 iken hiç render olmaz', () => {
    const { container } = render(<ShiftSummary oee={{ ...FULL, loaded_qty: 0 }} />)
    expect(container.firstChild).toBeNull()
  })
})

describe('hm süre biçimi', () => {
  it('90 dk altı düz dakika, üstü saatli biçim; yuvarlama taşması yok', () => {
    expect(hm(75)).toBe('75 dk')
    expect(hm(480)).toBe('8 s 00 dk')
    expect(hm(479.6)).toBe('8 s 00 dk') // toplam önce yuvarlanır; "7 s 60 dk" olmamalı
    expect(hm(150)).toBe('2 s 30 dk')
  })
})
```

- [ ] **Step 2: Testlerin başarısız olduğunu gör**

Run: `cd frontend && npm run test`
Expected: FAIL — `ShiftSummary.tsx` modülü yok / `hm` export edilmemiş.

- [ ] **Step 3: Implementasyon (5 dosya)**

(a) `frontend/src/api/types.ts` — `Oee` arayüzüne `calendar_min` satırından sonra ekle:

```ts
  // Vardiya künyesi bağlamı (spec 2026-07-03); eski backend yanıtlarında bulunmayabilir.
  loaded_qty?: number
  good_count?: number // nihai iyi; kartta gösterilmez (no-scrap → ≈yüklenen)
  redo_count?: number
  span_min?: number // gözlem penceresi (dk)
```

(b) `frontend/src/styles/theme.ts` — `tl` tanımından sonra ekle:

```ts
/** Tam sayı tr biçimi (binlik ayraç): 1240 → "1.240". */
export const num0 = (x: number): string => Math.round(x).toLocaleString('tr-TR')

/** Dakika → süre etiketi: 75 → "75 dk"; 480 → "8 s 00 dk" (≥90 dk saatli biçim).
 *  Önce toplam yuvarlanır ki "7 s 60 dk" gibi taşma olmasın. */
export const hm = (min: number): string => {
  const t = Math.round(min)
  if (t < 90) return `${t} dk`
  return `${Math.floor(t / 60)} s ${String(t % 60).padStart(2, '0')} dk`
}
```

(c) Create `frontend/src/components/ShiftSummary.tsx`:

```tsx
// Vardiya Künyesi: gözlem penceresi + parça sayıları (/oee bağlam alanları).
// "İyi (ilk geçiş)" = yüklenen − redo (Q'nun payıyla birebir; formül çoğaltma sayılmaz).
// good_count bilinçli gösterilmez: no-scrap modelinde ≈ yüklenen (kafa karıştırır).
import type { Oee } from '../api/types'
import { hm, num0 } from '../styles/theme'
import Card from './Card'

export default function ShiftSummary({ oee }: { oee: Oee }) {
  const { loaded_qty: loaded, redo_count: redo, span_min: span } = oee
  if (loaded == null || redo == null || span == null || loaded <= 0) return null
  return (
    <Card eyebrow="Vardiya Künyesi" period className="kunye">
      <dl className="kn-rows">
        <div className="kn-row">
          <dt>Gözlem penceresi</dt>
          <dd>{hm(span)}</dd>
        </div>
        <div className="kn-row kn-sep">
          <dt>Yüklenen</dt>
          <dd>{num0(loaded)} parça</dd>
        </div>
        <div className="kn-row">
          <dt>İyi (ilk geçiş)</dt>
          <dd>{num0(loaded - redo)} parça</dd>
        </div>
        <div className="kn-row">
          <dt>Redo</dt>
          <dd>{num0(redo)} parça</dd>
        </div>
      </dl>
    </Card>
  )
}
```

(d) `frontend/src/styles/theme.css` — dosya sonuna ekle:

```css
/* ── Vardiya Künyesi: hairline satırlar, sağa yaslı tabular değerler ── */
.kn-rows { margin: 0; }
.kn-row {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 7px 2px; border-bottom: 1px solid var(--line); font-size: 0.9rem;
}
.kn-row:last-child { border-bottom: 0; }
.kn-row dt { color: var(--muted); }
.kn-row dd {
  margin: 0; font-family: var(--mono);
  font-variant-numeric: tabular-nums; color: var(--ink);
}
.kn-sep { border-top: 2px solid var(--line); margin-top: 4px; }
```

(e) `frontend/src/views/Dashboard.tsx` — import bloğuna `import ShiftSummary from '../components/ShiftSummary'` ekle (alfabetik sıraya uy); TrendChart satırlarından sonra (Durum bölgesi içinde, `{detay && trendQ.isError && <CardError ... />}` satırının hemen altına) ekle:

```tsx
          {detay && oeeQ.data && <ShiftSummary oee={oeeQ.data} />}
```

- [ ] **Step 4: Testlerin geçtiğini gör + tam frontend zinciri**

Run: `cd frontend && npm run test`
Expected: tümü PASS (14 mevcut + 4 yeni).

Run: `cd frontend && npm run build && npm run lint`
Expected: `tsc -b` + vite build hatasız; eslint hatasız.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/styles/theme.ts frontend/src/components/ShiftSummary.tsx frontend/src/styles/theme.css frontend/src/views/Dashboard.tsx frontend/src/components/components.test.tsx
git commit -m "feat(pano): Vardiya Künyesi kartı (Detay) — pencere + yüklenen/ilk-geçiş/redo

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Uçtan uca doğrulama + dist senkronu

**Files:**
- Modify: `backend/app/frontend_dist/*` (yalnız `make frontend-sync` çıktısı — elle dokunma)

**Interfaces:**
- Consumes: Task 1 `/oee` alanları + Task 2 kartı.
- Produces: merge'e hazır branch (tüm süitler yeşil, dist güncel, görsel doğrulama yapılmış).

- [ ] **Step 1: Tam süitler**

Run: `make ci` (repo kökünde — ruff + backend pytest)
Expected: hatasız, tüm testler PASS.

Run: `cd frontend && npm run test`
Expected: tümü PASS.

- [ ] **Step 2: Dist senkronu (bayat-dist tuzağına karşı)**

Run: `make frontend-sync`
Expected: vite build + `backend/app/frontend_dist` yenilenir.

```bash
git add backend/app/frontend_dist
git commit -m "chore(dist): frontend-sync — vardiya künyesi

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 3: Uçtan uca göz kontrolü (yerel native run)**

Temiz DB ile backend'i başlat (eski .duckdb → BinderException tuzağı; `make clean` önce):

Run: `make clean && cd backend && uvicorn app.main:app --port 8000` (arka planda)

Tarayıcı/Playwright ile `http://localhost:8000`:
1. Bir senaryo yükle (üst bar) → **Detay** görünümünde Durum bölgesinde, trend grafiğinin ardından "Vardiya Künyesi" kartı görünür; değerler dolu ve `İyi (ilk geçiş) = Yüklenen − Redo` tutuyor.
2. **Özet** görünümüne geç → kart GÖRÜNMEZ.
3. `GET /oee` yanıtında 4 yeni alan mevcut (`curl -s localhost:8000/oee` ile).

Expected: üçü de doğru; ekran görüntüsü al (PR gövdesi için).

- [ ] **Step 4: Push + PR**

```bash
git push -u origin feat/vardiya-kunyesi
```

`gh pr create` ile PR aç — başlık: `Vardiya Künyesi kartı (PR #4'ün yalın yeniden doğuşu)`; gövdede: spec linki, "yalın varyant onaylı; kullanım/duruş dökümü bilinçli dışarıda", test sayıları, ekran görüntüsü, PR #4 kapatma referansı. Gövde şu satırla biter: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`

---

## Self-Review Notu

- Spec kapsaması: 4 alan (T1), yalın kart + görünürlük kuralı + yerleşim + biçim (T2), test/doğrulama zinciri (T1/T2/T3) — spec'teki her madde bir task'te. `downtime_union_min` eklenmedi (spec kapsam dışı bölümüyle tutarlı).
- Tip tutarlılığı: backend `float` alanlar ↔ frontend `number?`; `_quality_metrics` 5'li tuple imzası yalnız `compute_oee`'de kullanılıyor (grep ile doğrulandı, başka çağıran yok).
- `OeeResult` hiçbir yerde 7'den fazla pozisyonel argümanla kurulmuyor; yeni alanlar keyword ile geçiliyor.

# OEE Hazırlık — Dalga C (H8→H9) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Kanonik kayıt yeri:** Onaylanınca `oee-platform/docs/superpowers/plans/2026-06-30-oee-hazirlik-dalga-c.md`.

## Context

Hazırlık **Dalga A (H1–H3)** ve **Dalga B (H4–H7)** tamamlandı (sibling branch'ler, merge bekliyor). Son dalga **C: operasyonel sağlamlık** — H1-H9 dokümanının kalan iki paketi:
- **H8** — Utilization/takvim modeli paritesi (gerçek OEE kredibilitesi).
- **H9** — Ops hızlı kazanımlar (loglama, hata mesajları, performans; auth+deploy kısmen mevcut).

**Goal:** Utilization'ı gerçek vardiya/mola/bakım takvimine dayandır (H8); loglama + tutarlı hata + performans güvencesi + deploy dokümanı ekle (H9).

**Architecture:** H8 platformun bugün ATTIĞI `shifts`/`breaks`/`workdays` takvim bloğunu ayrıştırır (`config.py` bugün yalnız `planned_maintenance` okuyor), `analytics/calendar.py`'de **takvim-dakikası** hesaplar ve `/oee` utilization'ını `operating / span+planned` MVP'sinden `operating / takvim-dakikası`'na geçirir. H9 stdlib logging + zamanlama middleware'i (auth middleware deseni), global hata yakalayıcı, ölçekli perf-smoke ve `docs/deployment.md` ekler. Katman ayrımı + firewall korunur.

> **H8 parite notu (keşif düzeltmesi):** Simülatör utilization HESAPLAMIYOR (`grep utilization simulator/src` = 0); `schedule.py` Calendar yalnız yükleme-iznini geçitler. Dolayısıyla parite mevcut bir sim sayısına eşleme DEĞİL — her iki tarafın da kullandığı **aynı `line_default.yaml` takvim bloğundan** türetilen takvim-dakikası modelini kurup, bilinen pencereler için **analitik beklentiyle** (örn. 1 iş günü = 2×8s − 2×15dk mola = 930 dk) doğrularız. Bu, "±%1 sim parite" kriterinin sahadaki doğru karşılığıdır.

**Tech Stack:** Python 3.11 · FastAPI · DuckDB · frozen dataclass config · pytest · stdlib `logging` (yeni bağımlılık yok) · ruff.

## Global Constraints

- **A/P/Q/OEE DEĞİŞMEZ:** H8 yalnız `utilization`'ı değiştirir; availability/performance/quality/oee ve `final_yield` aynen kalır (mevcut parite/regresyon eşikleri `PARITY_TOL=0.01` korunur).
- **Firewall + katman ayrımı:** yeni analitik `ground_truth` ALMAZ; iş mantığı DuckDB'yi tanımaz.
- **Config deseni:** takvim ayrıştırma = frozen dataclass + `load_*` (yaml.safe_load + coercion); hafta-günü adı→int eşlemesi simülatör `config.py:_WEEKDAYS` desenini izler. Vardiyalar gece-yarısını AŞMAZ (simülatör varsayımı).
- **Env/feature deseni:** `os.environ.get("OEE_*", default)` lazy; logging seviyesi `OEE_LOG_LEVEL` (varsayılan INFO).
- **CI yeşil:** `make ci` (ruff + pytest) + frontend `npm` zincirleri yeşil kalır. CLI/log çıktıları ASCII-güvenli (Windows cp1252 tuzağı).
- **Geriye uyumluluk:** `compute_oee` yeni `calendar_min` param'ı OPSİYONEL (trend/replay/testler değişmeden çalışır).
- Dil: kod İngilizce, yorum/docstring Türkçe.

---

## Task 0: Branch kurulumu

- [ ] **Step 1:** Dalga A/B branch'leri korunur. main'den dallan: `git checkout main && git checkout -b feat/dalga-c-h8-h9`.
- [ ] **Step 2:** Planı repoya kopyala: `docs/superpowers/plans/2026-06-30-oee-hazirlik-dalga-c.md`; commit `docs: H8-H9 (Dalga C) uygulama planı`.

---

# H8 — Utilization / takvim modeli paritesi

**Hedef:** Vardiya/mola/planlı bakım takvimini doğru modelle; utilization = çalışılan / takvim-zamanı. Planlı bakım çift sayılmasın, vardiya-dışı dışlansın.

### Task 1: Takvim ayrıştırma (`load_calendar` + `CalendarDef`)

**Files:**
- Modify: `oee-platform/backend/app/config.py` (`CalendarDef` dataclass + `load_calendar(path)`; mevcut `load_planned_maintenance` korunur/yeniden kullanılır)
- Test: `oee-platform/backend/tests/test_calendar_config.py`

**Interfaces — Produces:**
```python
@dataclass(frozen=True)
class ShiftDef:   start_min: int; end_min: int        # gün içi dakika [0,1440)
@dataclass(frozen=True)
class BreakDef:   start_min: int; duration_min: float
@dataclass(frozen=True)
class CalendarDef:
    workdays: tuple[int, ...]        # 0=Pazartesi (simülatör _WEEKDAYS ile aynı)
    shifts: tuple[ShiftDef, ...]
    breaks: tuple[BreakDef, ...]
    maintenance: tuple[MaintenanceWindow, ...]   # mevcut MaintenanceWindow yeniden kullanılır
def load_calendar(path: str | Path) -> CalendarDef
_WEEKDAYS = {"Mon":0,"Tue":1,"Wed":2,"Thu":3,"Fri":4,"Sat":5,"Sun":6}
def _hhmm_to_min(s: str) -> int   # "06:00" -> 360
```

- [ ] **Step 1:** Failing test — `load_calendar(LINE_CONFIG)`: workdays=(0,1,2,3,4); 2 shift (360–840, 840–1320); 2 break; 1 maintenance. `_hhmm_to_min("14:00")==840`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Impl `load_calendar` (calendar bloğunu ayrıştır; eksik bloklar → boş tuple, geriye uyumlu). `load_planned_maintenance` mantığını `MaintenanceWindow` üretmek için yeniden kullan.
- [ ] **Step 4:** Run → PASS; ruff + mevcut config testleri yeşil.
- [ ] **Step 5:** Commit: `feat(h8): takvim ayrıştırma (load_calendar + CalendarDef)`.

### Task 2: `calendar.py` — takvim-dakikası hesabı

**Files:**
- Create: `oee-platform/backend/app/analytics/calendar.py`
- Test: `oee-platform/backend/tests/test_calendar_minutes.py`

**Interfaces — Produces:**
```python
def calendar_minutes(frm: datetime, to: datetime, cal: CalendarDef) -> float:
    # [frm,to) içinde: workday + vardiya içi + mola-dışı + bakım-dışı dakikaların toplamı.
    # Gün gün yürür; her gün vardiya∩pencere − molalar − o güne düşen bakım.
```
Yaklaşım: günlük döngü; her workday için her shift'in pencere ile kesişimi; o kesişime düşen breaks ve maintenance pencereleri çıkarılır (çift sayım yok). `_norm` (oee.py) ISO→datetime deseni yeniden kullanılır.

- [ ] **Step 1:** Failing test — bilinen pencereler (epoch 2026-01-05 Pzt 06:00):
```python
def test_one_full_workday_minutes():
    # Pzt 06:00 -> Salı 06:00: 2x8s=960 − 2x15dk mola = 930 dk
    assert calendar_minutes(dt("2026-01-05 06:00"), dt("2026-01-06 06:00"), CAL) == 930

def test_weekend_is_zero():
    assert calendar_minutes(dt("2026-01-10 06:00"), dt("2026-01-12 06:00"), CAL) == 0  # Cmt+Paz

def test_maintenance_subtracted_once():
    # bakım 2026-01-07 22:00 +120dk; vardiya-dışına taşan kısmı çift düşülmez
    ...
def test_offshift_excluded():
    # 22:00-06:00 arası (vardiya dışı) takvime girmez
    ...
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Impl `calendar_minutes` (gün gün; shift∩window − break∩ − maintenance∩; örtüşme bir kez).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `feat(h8): takvim-dakikası hesabı (calendar.py)`.

### Task 3: Utilization'ı takvime bağla (`oee.py` + route)

**Files:**
- Modify: `oee-platform/backend/app/analytics/oee.py` (`compute_oee` opsiyonel `calendar_min`)
- Modify: `oee-platform/backend/app/api/oee_routes.py` (pencere için `calendar_minutes` hesapla + besle)
- Test: `oee-platform/backend/tests/test_utilization_calendar.py`, mevcut `test_oee_endpoint.py`

**Interfaces — Consumes:** `calendar_minutes`, `load_calendar`. **Produces:** `compute_oee(events, production, line, planned_downtime_min=0.0, calendar_min=None)`; `calendar_min` verilirse `utilization = clamp01(operating / calendar_min)`, yoksa eski MVP (span+planned) — geriye uyumlu. Route, pencere [frm,to] (yoksa olay min/max'ı) için `calendar_minutes` hesaplar.

- [ ] **Step 1:** Failing test — `test_utilization_calendar.py`: baseline'da utilization = operating/takvim-dakikası (0<util≤1, makul); planlı bakım çift sayılmaz; A/P/Q/oee `compute_oee` ile DEĞİŞMEZ (yalnız utilization değişir). `test_oee_endpoint`: utilization sayısal ve (0,1].
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Impl: `compute_oee`'ye `calendar_min` param; route `calendar_minutes` ile besle (config'ten `load_calendar`). Mevcut `_planned_downtime` korunur (rapor için).
- [ ] **Step 4:** Run → PASS; `make ci` + regression (A/P/Q/oee parite) yeşil.
- [ ] **Step 5:** Commit: `feat(h8): utilization = çalışılan / takvim-zamanı (vardiya/mola/bakım)`.

**H8 Başarı kriteri:** Utilization gerçek takvimden (vardiya−mola−bakım) hesaplanıyor; planlı bakım çift sayılmıyor; vardiya-dışı dışlanıyor; A/P/Q/OEE parite testleri bozulmadan geçiyor.

---

# H9 — Ops hızlı kazanımlar

**Hedef:** Pano müşteriye link ile açılacaksa gereken temel sağlamlık: loglama, açık hata, performans güvencesi, deploy dokümanı. (Auth + Docker/Render zaten var.)

### Task 4: Yapılandırılmış loglama + zamanlama middleware

**Files:**
- Modify: `oee-platform/backend/app/main.py` (lifespan'de `logging.basicConfig`; `@app.middleware("http")` zamanlama logu)
- Create: `oee-platform/backend/app/logging_setup.py` (küçük yardımcı: seviye env'den, format)
- Modify: `oee-platform/backend/app/ingest/loader.py` (ingest özeti log)
- Test: `oee-platform/backend/tests/test_logging.py`

**Interfaces — Produces:** `setup_logging()` (stdlib `logging.basicConfig`, `OEE_LOG_LEVEL`); request middleware her isteği `method path status duration_ms` ile loglar (auth `_auth_gate` deseninin yanına).

- [ ] **Step 1:** Failing test — `caplog` ile: bir isteğin (`/health`) `method`/`path`/`status`/`duration_ms` içeren log satırı ürettiğini doğrula; `setup_logging()` `OEE_LOG_LEVEL=DEBUG` ile DEBUG seviyesini kurar.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Impl `logging_setup.py` + lifespan çağrısı + timing middleware (`time.perf_counter` ile süre; ASCII log). Loader ingest sonunda `accepted/rejected` özetini loglar.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `feat(h9): yapılandırılmış loglama + istek zamanlama middleware`.

### Task 5: Tutarlı hata yönetimi (global handler + tarih doğrulama)

**Files:**
- Modify: `oee-platform/backend/app/main.py` (`@app.exception_handler(ValueError)` → 400 tutarlı `{detail}`)
- Create: `oee-platform/backend/app/api/_params.py` (`parse_range(frm, to)` → datetime|None; bozuk tarih → `ValueError` açık mesaj)
- Modify: analitik route'lar (`oee_routes`, `loss_tree_routes`, `cost_routes`, `trend_routes`, `recommend_routes`) — ham `frm/to`'yu `parse_range` ile doğrula (bozuk → 400, 500 değil)
- Test: `oee-platform/backend/tests/test_error_handling.py`

**Interfaces — Produces:** `parse_range(frm, to) -> tuple[datetime|None, datetime|None]` (boş→None; geçersiz format → `ValueError("geçersiz tarih: ...")`). Global handler ValueError→`JSONResponse(400, {"detail": ...})`.

- [ ] **Step 1:** Failing test — `GET /oee?from=BOZUK` → **400** (500 değil), `detail` açık; geçerli tarih çalışır.
- [ ] **Step 2:** Run → FAIL (şu an 500).
- [ ] **Step 3:** Impl `parse_range` + global ValueError handler + route'larda kullan. Mevcut 404 mesajları korunur.
- [ ] **Step 4:** Run → PASS; `make ci` yeşil.
- [ ] **Step 5:** Commit: `feat(h9): tutarlı hata yönetimi (400 + global handler + tarih doğrulama)`.

### Task 6: Performans smoke testi

**Files:**
- Create: `oee-platform/backend/tests/test_perf_smoke.py`

**Yaklaşım (büyük fixture commit'lemeden):** baseline events/production'ı K=6 haftalık-ofsetli kopyayla ölçekle (carrier_id'ler `CAR-Wk-...` ile benzersizleştirilir; hat-seviyesi olaylar carrier'sız) → ~12 hafta hacmi (~9–10k olay), `tmp_path`'e yaz, ingest et, pano uçlarını zamanla.

- [ ] **Step 1:** Failing test — ölçekli veride `/oee`, `/loss-tree/cost`, `/oee/trend?bucket=day` her biri `< PERF_BUDGET_S` (ör. 2.0s); ingest çökmez. (`@pytest.mark.perf`.)
```python
def test_dashboard_under_budget(tmp_path, monkeypatch):
    scaled = _scale_baseline(tmp_path, weeks=6)   # benzersiz carrier_id + haftalık ofset
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "perf.duckdb"))
    with TestClient(app) as client:
        client.post("/ingest", json={"path": str(scaled)})
        for ep in ("/oee", "/loss-tree/cost", "/oee/trend?bucket=day"):
            t = time.perf_counter(); r = client.get(ep); dt = time.perf_counter() - t
            assert r.status_code == 200 and dt < PERF_BUDGET_S, f"{ep}: {dt:.2f}s"
```
- [ ] **Step 2:** Run → ölçek yardımcısı/eşik ile FAIL (yardımcı yok).
- [ ] **Step 3:** `_scale_baseline` yardımcısı (baseline CSV oku, K kez haftalık ofset + carrier_id suffix; orders aynen). Eşik `PERF_BUDGET_S=2.0`.
- [ ] **Step 4:** Run → PASS. (Geçmezse en yavaş uç `/oee/trend` — bucket başına `compute_oee`; gerekiyorsa not düş, optimize ayrı görev.)
- [ ] **Step 5:** Commit: `test(h9): performans smoke (ölçekli ~12 hafta, pano < 2s)`.

### Task 7: Deploy dokümanı

**Files:**
- Create: `oee-platform/docs/deployment.md`

İçerik: tek-müşteri kurulum (Render Blueprint adımları, `render.yaml` + `backend/Dockerfile` özeti), env tablosu (`OEE_AUTH_PASS/USER/SECRET`, `SAMPLE_DATA_DIR`, `OEE_*_CONFIG`, `OEE_LOG_LEVEL`, `$PORT`), HTTPS notu, Railway/Fly taşınabilirliği, DuckDB kalıcılık uyarısı (ephemeral; açılışta baseline auto-ingest). STATUS.md §Deploy'dan derlenir + H9 logging/auth eklenir.

- [ ] **Step 1:** `docs/deployment.md` yaz (yalnız doküman; kod yok).
- [ ] **Step 2:** Commit: `docs(h9): tek-müşteri deploy kılavuzu (deployment.md)`.

**H9 Başarı kriteri:** Loglar isteği/ingest'i/süreyi gösteriyor; bozuk girdi açık 400 veriyor; ölçekli veride pano < 2s; deploy dokümanı tek-müşteri kurulumu kapsıyor; auth korumalı uçlar token'sız 401 (mevcut). Tüm testler + CI yeşil.

---

## Doğrulama (uçtan uca)

1. **Platform:** `make ci` → ruff + tüm pytest (yeni H8/H9 + mevcut regression; A/P/Q/OEE parite bozulmadan) yeşil.
2. **H8 elle:** `GET /oee` → `utilization` takvimden makul (0<util≤1); bilinen pencere için `calendar_minutes` analitik beklentiyle (930/gün) eşleşir.
3. **H9 loglama:** sunucu çalışırken her istek `method path status duration_ms` loglar; ingest özeti loglanır.
4. **H9 hata:** `GET /oee?from=xx` → 400 açık `detail` (500 değil).
5. **H9 perf:** `test_perf_smoke` (ölçekli ~12 hafta) pano uçları < 2s.
6. **H9 deploy:** `docs/deployment.md` env + HTTPS + tek-müşteri akışını kapsar.
7. **Firewall:** yeni analitik (`calendar_minutes`) imzasında `ground_truth` yok.

## Tamamlanınca

- Branch `feat/dalga-c-h8-h9` → PR → `main` (A/B PR'larıyla bağımsız).
- `docs/STATUS.md`: Hazırlık Dalga A+B+C TAMAM; H1–H9 bitti → sırada **pilot kiti / saha denemesi**.
- Planı repoya kopyala (Task 0 Step 2).

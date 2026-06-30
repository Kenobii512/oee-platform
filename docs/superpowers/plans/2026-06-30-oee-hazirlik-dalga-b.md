# OEE Hazırlık — Dalga B (H4→H5→H6→H7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Kanonik kayıt yeri:** Onaylanınca `oee-platform/docs/superpowers/plans/2026-06-30-oee-hazirlik-dalga-b.md` olarak repoya kopyalanacak.

## Context

Hazırlık **Dalga A (H1→H2→H3)** tamamlandı (`feat/h1-dirty-data`, 11 commit, backend 145 + frontend 8 yeşil; merge bekliyor). Sırada H1-H9 dokümanının **Dalga B**'si: *derinlik + demo gücü*. Dört paket:
- **H4** — Çok-seed istatistiksel doğrulama + simülatör hat varyasyonları (pariteyi tek seed yerine dağılım olarak kanıtla).
- **H5** — Duyarlılık analizi (param → OEE etkisi; öneri önceliklendirme + what-if temeli).
- **H6** — Demo cilası (senaryo anlatısı + "neye bak"; satışın kaldıracı).
- **H7** — Hat-tanımı doğrulayıcı (pilot kurulum sürtünmesini düşür).

**Goal:** Pariteyi dağılım olarak kanıtla (H4), hangi parametrenin OEE'yi en çok oynattığını ölç (H5), demoyu kendi kendini anlatır yap (H6), yeni hattın hatasız modellenmesini sağla (H7).

**Architecture:** H4/H5 ağırlıkla **simülatör** (`simulator/`, kendi `.venv`'i) + platform regresyon fixture'ları; çok-seed goldenlar `_generate.py` deseniyle bir kez üretilip commit'lenir, platform testi canlı kodla yeniden hesaplayıp **dağılım** doğrular. H6 mevcut senaryo kataloğu + dropdown'a `narrative`/`highlight` alanı ekler (yeni analitik yok). H7 platform `load_line_definition`'a kurallı doğrulama + `POST /line/validate` ekler. Firewall ve katman ayrımı korunur.

**Tech Stack:** Python 3.11 · simülatör (`src/line.py` `run_simulation`, `src/metrics.py`, `src/accuracy.py`, frozen `Scenario` dataclass'ları) · FastAPI · pytest (`@pytest.mark.regression`) · React 19 + Vite (H6) · ruff.

## Global Constraints

- **Firewall:** çıkarım/analitik imzaları `ground_truth` ALMAZ; ground_truth yalnız test/golden üretiminde. H4 platform testi `extract_loss_tree(events, production, line)` ile çalışır.
- **İki ayrı venv:** simülatör işleri (H4 üretim/varyasyon, H5 sweep, sim testleri) `simulator/.venv` + `simulator/`'dan çalışır; platform testleri `oee-platform/backend/.venv`. Simülatör platform test venv'inde import EDİLEMEZ → platform çok-seed testi **commit'li fixture** okur (canlı sim çağırmaz).
- **Determinizm:** `run_simulation(config, seed, scenario)` global state YOK; sweep/çok-seed `dataclasses.replace` ile parametre değiştirir (mevcut `run.py:35` deseni). Seed'ler sabit liste; `Math.random`/argless `Date` yok.
- **Regresyon eşikleri korunur** (`test_regression_contract.py`): `PARITY_TOL=0.01`, `LOSSLESS_MIN=0.95`, `INFERRED_MIN=0.85`, `REDO_MIN=0.70`, `VISIBLE_TOL=0.01`. H4 yeni dağılım eşikleri bunlarla tutarlı.
- **Config deseni:** yeni alanlar = frozen dataclass + `load_*` (yaml.safe_load + coercion); `ScenarioInfo` `__dict__` ile otomatik serialize (`GET /scenarios`).
- **CI yeşil:** platform `make ci` (ruff + pytest) ve `simulator` testleri (105+) yeşil kalır; frontend `npm run lint/test/build`. CLI çıktıları ASCII-güvenli (Windows cp1252 — Dalga A tuzağı).
- **Fixture bloat sınırı:** çok-seed CSV setleri için **N=10** (gerekçe: dağılım için yeterli, repo şişmesi makul). Düşürülen kapsam `log`/yorumla belirtilir.
- Dil: kod İngilizce, yorum/docstring Türkçe.

---

## Task 0: Branch kurulumu

- [ ] **Step 1:** `feat/h1-dirty-data` korunur (Dalga A, merge bekliyor). Dalga B bağımsız → main'den dallan: `git checkout main && git checkout -b feat/dalga-b-h4-h7`.
- [ ] **Step 2:** Planı repoya kopyala: `oee-platform/docs/superpowers/plans/2026-06-30-oee-hazirlik-dalga-b.md`; commit `docs: H4-H7 (Dalga B) uygulama planı`.

---

# H4 — Çok-seed istatistiksel doğrulama + hat varyasyonları

**Hedef:** OEE pariteyi ve gizli-kanal geri kazanımını **dağılım** olarak kanıtla; simülatöre 2 gerçekçi hat varyasyonu ekleyip akıl-sağlığını koru.

### Task 1: Çok-seed golden üreteci + commit'li fixture

**Files:**
- Modify: `oee-platform/backend/tests/fixtures/_generate.py` (N-seed döngüsü ekle)
- Create: `oee-platform/backend/tests/fixtures/multiseed/seed_<n>/{events,production,orders,ground_truth}.csv` (N=10)
- Create: `oee-platform/backend/tests/fixtures/multiseed_golden.json`

**Interfaces — Consumes (simülatör):** `load_config(path)`, `load_scenario(path)` (`scenario_baseline.yaml`), `run_simulation(config, seed, scenario) -> SimResult`, `metrics.compute_oee(result, config) -> OEE(availability,performance,quality,oee,final_yield)`, `Recorder.write_csvs(out_dir, carriers, orders)`.
**Produces:** `multiseed_golden.json`:
```json
{"seeds": [42, 7, 123, ...],
 "per_seed": {"42": {"availability":.., "performance":.., "quality":.., "oee":.., "final_yield":..}, ...}}
```
(yalnız simülatör-referans OEE; platform parite testi CSV'lerden CANLI yeniden hesaplar.)

- [ ] **Step 1:** `_generate.py`'ye `SEEDS = (42, 7, 123, 1, 999, 2024, 13, 77, 256, 8)` (N=10) ekle; her seed için baseline senaryosunu çalıştır, CSV setini `multiseed/seed_<n>/`'e yaz, sim OEE'sini `per_seed`'e topla, `multiseed_golden.json` yaz. (Mevcut baseline/lossless üretimi korunur.)
- [ ] **Step 2:** Üreteci simülatör venv'iyle çalıştır: `cd oee-platform/backend && ../../simulator/.venv/Scripts/python.exe tests/fixtures/_generate.py` (mevcut çalıştırma yolu); 10 seed dizini + json üretilir. CSV satır-sonu LF.
- [ ] **Step 3:** Üretilen fixture'ları commit'le: `test(h4): N=10 çok-seed golden fixture seti + sim OEE özeti`.

### Task 2: Platform çok-seed parite + geri-kazanım dağılım testi

**Files:**
- Create: `oee-platform/backend/tests/test_multiseed_parity.py`
- Modify: `oee-platform/backend/tests/conftest.py` (`MULTISEED = FIXTURES / "multiseed"` + golden yükleyici)

**Interfaces — Consumes:** `load_fixture_into_repo(dir, db_path)`, `compute_oee(events, production, line)`, `extract_loss_tree(...)`, seed dizinindeki `ground_truth.csv` (test-tarafı truth, conftest `baseline_truth_value` deseniyle seed-bazlı genelleştir).

- [ ] **Step 1:** Failing test — `test_multiseed_parity.py` (`pytestmark = pytest.mark.regression`):
```python
def test_oee_parity_distribution():
    diffs = []
    for seed in SEEDS:
        repo = load_fixture_into_repo(MULTISEED / f"seed_{seed}", tmp_db(seed))
        res = compute_oee(repo.fetch_events(), repo.fetch_production(), LINE)
        g = GOLDEN["per_seed"][str(seed)]
        diffs.append(abs(res.oee - g["oee"]))
        assert abs(res.oee - g["oee"]) <= SEED_FLOOR_TOL   # hiçbir seed taban-altı değil (ör. 0.02)
        repo.close()
    assert mean(diffs) <= PARITY_TOL                       # ortalama ±%1

def test_inferred_recovery_distribution():
    recoveries = {"FILL_LOSS": [], "SPEED_LOSS": []}
    for seed in SEEDS:
        # extract_loss_tree value / seed_truth(cat) topla
        ...
    assert median(recoveries["FILL_LOSS"]) >= INFERRED_MIN  # medyan ≥ %85
    assert median(recoveries["SPEED_LOSS"]) >= INFERRED_MIN
```
- [ ] **Step 2:** Run → FAIL (test yok / yardımcı yok). `pytest tests/test_multiseed_parity.py -v`.
- [ ] **Step 3:** conftest'e `MULTISEED` + `seed_truth_value(seed, category)` (baseline_truth_value'un seed-parametrik kopyası) + `multiseed_golden` yükleyici ekle; testi tamamla. Eşik sabitleri açık (`SEED_FLOOR_TOL=0.02`).
- [ ] **Step 4:** Run → PASS; `make ci` + mevcut regression yeşil.
- [ ] **Step 5:** Commit: `test(h4): çok-seed OEE parite + gizli-kanal geri kazanım dağılım kapısı`.

### Task 3: Simülatör hat varyasyonları + akıl-sağlığı

**Files:**
- Create: `simulator/config/lines/line_fast_bottleneck.yaml`, `simulator/config/lines/line_long_shift.yaml` (mevcut `line_default.yaml`'dan türetilmiş; farklı darboğaz tankı / vardiya / süre profili)
- Create: `simulator/tests/test_line_variations.py`

**Interfaces — Consumes:** `load_config(path)`, `run_simulation(config, seed)`, `compute_oee(result, config)`. Mevcut bottleneck guard (`line.py:107-110`: tam 1 bottleneck) varyasyonlarda korunur.

- [ ] **Step 1:** Failing sim test — her varyasyon için: kayıpsız (scenario=None) `oee >= 0.95`; tam 1 bottleneck; çökme yok.
```python
@pytest.mark.parametrize("line_yaml", ["line_fast_bottleneck.yaml", "line_long_shift.yaml"])
def test_variation_lossless_sane(line_yaml):
    cfg = load_config(LINES / line_yaml)
    res = run_simulation(cfg, seed=42)            # scenario yok = kayıpsız
    assert compute_oee(res, cfg).oee >= 0.95
```
- [ ] **Step 2:** Run (simülatör venv) → FAIL (YAML yok).
- [ ] **Step 3:** 2 varyasyon YAML'ı ekle (her biri tam 1 bottleneck, makul time_min≤time_max, kapasite>0).
- [ ] **Step 4:** Run → PASS: `cd simulator && .venv/Scripts/python.exe -m pytest tests/test_line_variations.py -q`.
- [ ] **Step 5:** Commit: `feat(h4): 2 simülatör hat varyasyonu + akıl-sağlığı testi`.

**H4 Başarı kriteri:** N-seed OEE parite ortalaması ±%1 ve hiçbir seed taban-altı değil; gizli-kanal geri kazanım medyanı ≥%85; hat varyasyonları akıl-sağlığını geçer; tüm testler + CI yeşil.

---

# H5 — Duyarlılık analizi (parametre → OEE etkisi)

**Hedef:** Hangi parametrenin OEE'yi en çok oynattığını ölç → öneri önceliklendirme + what-if temeli.

### Task 4: Parametre-sweep aracı + etki tablosu

**Files:**
- Create: `simulator/tools/sensitivity.py` (sweep çerçevesi + CLI + rapor üretimi)
- Create: `simulator/tools/__init__.py`
- Create: `simulator/tests/test_sensitivity.py`
- Create (üretilen): `oee-platform/docs/sensitivity_report.md`

**Interfaces — Produces:**
```python
# parametre tek tek aralıkta oynatılır; her noktada OEE + kayıp ölçülür.
def sweep(param: str, values: list[float], seed: int = 42) -> list[dict]:
    # [{param, value, oee, availability, performance, quality, fill_loss, speed_loss, downtime_min}, ...]
def sensitivity_table(seeds=(42,7,123)) -> list[dict]:
    # [{param, oee_delta, direction}, ...] azalan |oee_delta|
def main(argv=None) -> int  # CLI: --report docs/sensitivity_report.md
```
Sweep, frozen `Scenario`'yu `dataclasses.replace` ile değiştirir: doluluk (`fill_loss.mean`), hız (`speed_loss.factor_mean`), MTBF/MTTR (`failures[i].mtbf_min/mttr_min`), mikro duruş (`microstops.target`/`mean_interval_min`).

- [ ] **Step 1:** Failing test — `test_sensitivity.py`: işaret/monotonluk akıl-sağlığı:
```python
def test_fill_rate_monotonic():
    rows = sweep("fill_loss.mean", [0.0, 5.0, 10.0], seed=42)
    fills = [r["fill_loss"] for r in rows]
    assert fills == sorted(fills)         # doluluk kaybı parametresi ↑ -> FILL_LOSS ↑ (monoton)

def test_speed_factor_lowers_performance():
    rows = sweep("speed_loss.factor_mean", [0.0, 0.1, 0.2], seed=42)
    perf = [r["performance"] for r in rows]
    assert perf[0] >= perf[-1]            # hız kaybı ↑ -> Performance ↓
```
- [ ] **Step 2:** Run (sim venv) → FAIL.
- [ ] **Step 3:** `sensitivity.py` impl: param yol-çözümleme (`"fill_loss.mean"` → nested replace), sweep döngüsü (run_simulation + compute_oee + accuracy/loss), `sensitivity_table` azalan etki; `main` raporu yazar.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Raporu üret + commit: `cd simulator && .venv/Scripts/python.exe -m tools.sensitivity --report ../oee-platform/docs/sensitivity_report.md`. Commit: `feat(h5): duyarlılık sweep aracı + etki tablosu + örnek rapor`.

**H5 Başarı kriteri:** Etki tablosu üretiliyor ve beklenen yönde (doluluk↑→FILL↑, hız↑→Performance↓); en etkili parametreler tutarlı sıralanıyor; örnek rapor demo/satış anlatısını besliyor.

> Opsiyonel köprü (YAGNI — ayrı görev): platform recommend eşit TL'de duyarlılığı yüksek kaybı öne alabilir. Bu planda HARİÇ; sensitivity çıktısı GainEstimator arayüzüyle uyumlu kalır.

---

# H6 — Demo cilası

**Hedef:** Demoyu kendi kendini anlatır yap — senaryo başına anlatı + "neye bak". (Tour framework değil; mevcut katalog + dropdown'a anlatı.)

### Task 5: Senaryo kataloğuna `narrative` + `highlight` (backend)

**Files:**
- Modify: `oee-platform/config/scenarios.yaml` (her senaryoya `narrative` + `highlight`)
- Modify: `oee-platform/backend/app/config.py` (`ScenarioInfo` + `load_scenario_catalog`)
- Test: `oee-platform/backend/tests/test_scenarios_catalog.py` (varsa genişlet, yoksa ekle)

**Interfaces — Produces:** `ScenarioInfo(id, title, description, expected_top_loss, data_dir, narrative, highlight)`. `GET /scenarios` `s.__dict__` ile yeni alanları otomatik döndürür. `highlight ∈ {"cost","loss_tree","trend","oee"}` (panoda vurgulanacak grafik anahtarı).

- [ ] **Step 1:** Failing test — `GET /scenarios` her senaryoda `narrative` (boş değil) + `highlight` döndürür.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** `ScenarioInfo`'ya 2 alan (geriye uyumlu default `""`/`"cost"`); loader `.get(...)`; `scenarios.yaml`'a 6 senaryo için bir-cümle anlatı + highlight.
- [ ] **Step 4:** Run → PASS; `make ci` yeşil.
- [ ] **Step 5:** Commit: `feat(h6): senaryo kataloğuna anlatı + vurgu alanı`.

### Task 6: Pano senaryo anlatısı (frontend)

**Files:**
- Modify: `oee-platform/frontend/src/api/types.ts` (`ScenarioInfo` → `narrative?`, `highlight?`)
- Modify: `oee-platform/frontend/src/components/ScenarioDropdown.tsx` (anlatıyı render et)
- Test: `oee-platform/frontend/src/components/components.test.tsx` (dropdown anlatı smoke)

- [ ] **Step 1:** Failing vitest — seçili senaryonun `narrative` metni DOM'da.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** `ScenarioInfo` tipine alanlar; dropdown her seçenekte `s.narrative`'i `<span>` ile gösterir (mevcut title/description/expected_top_loss deseni). DESIGN.md yönü korunur (sakin, mono, neon yok).
- [ ] **Step 4:** Run → PASS; `npm run lint && npm run build` yeşil.
- [ ] **Step 5:** Commit: `feat(h6): pano senaryo anlatısı (dropdown)`.

**H6 Başarı kriteri:** Her senaryo için hikâye görünüyor; demo kendi kendini anlatır akışa yaklaşır; frontend testleri + lint + build yeşil.

---

# H7 — Hat-tanımı doğrulayıcı

**Hedef:** Yeni hattın hatasız/hızlı modellenmesi — pilot kurulum sürtünmesini düşür.

### Task 7: Kurallı doğrulama (`validate_line`) + `POST /line/validate`

**Files:**
- Create: `oee-platform/backend/app/config_validate.py` (`validate_line_dict(raw) -> list[str]`)
- Modify: `oee-platform/backend/app/config.py` (`load_line_definition` opsiyonel `validate=True` ile çağırır)
- Create: `oee-platform/backend/app/api/line_routes.py` (`POST /line/validate`)
- Modify: `oee-platform/backend/app/main.py` (router'ı ekle)
- Create: `oee-platform/backend/tests/test_line_validate.py`
- Create: `oee-platform/docs/line-definition-guide.md`

**Interfaces — Produces:**
```python
def validate_line_dict(raw: dict) -> list[str]:
    # eyleme dönük hata listesi (boş = geçerli). Kurallar:
    #  - line.id zorunlu
    #  - tanks boş değil; her tank id/time_min/time_max zorunlu; time_min <= time_max; capacity > 0
    #  - tam 1 bottleneck (sum(bottleneck)==1) -- sim line.py:107-110 ile hizalı
    #  - orders[].carrier_qty > 0 (Quality paydası)
class LineValidationError(ValueError): ...
```
`POST /line/validate` gövdesi: ham YAML/JSON line dict → `{"valid": bool, "errors": [...]}` (200; her zaman, 4xx değil — doğrulama sonucu veridir).

- [ ] **Step 1:** Failing test — `test_line_validate.py`:
```python
def test_valid_line_passes():
    assert validate_line_dict(VALID) == []

@pytest.mark.parametrize("mutate,msg", [
    (lambda d: d["tanks"][0].pop("time_min"), "time_min"),
    (lambda d: _set_two_bottlenecks(d), "bottleneck"),
    (lambda d: d["tanks"][0].update(capacity=0), "capacity"),
    (lambda d: d["tanks"][0].update(time_min=99, time_max=1), "time_min"),
])
def test_invalid_line_caught(mutate, msg):
    d = copy.deepcopy(VALID); mutate(d)
    errs = validate_line_dict(d)
    assert any(msg in e for e in errs)
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** `validate_line_dict` impl (kural listesi, eyleme dönük mesajlar); `POST /line/validate` route + main router; `load_line_definition` opsiyonel `validate` (varsayılan davranış kırılmaz).
- [ ] **Step 4:** Run → PASS; `make ci` yeşil. Mevcut `line_default.yaml` geçerli doğrulanmalı (regresyon yok).
- [ ] **Step 5:** `docs/line-definition-guide.md` yazım kılavuzu (pilot kiti çekirdeği). Commit: `feat(h7): hat-tanımı doğrulayıcı + POST /line/validate + kılavuz`.

**H7 Başarı kriteri:** Geçerli tanım geçer; her geçersizlik türü açık mesajla yakalanır; mevcut `line_default.yaml` geçerli; kılavuz bir kişinin yardımsız hat modellemesine yeter.

---

## Doğrulama (uçtan uca)

1. **Platform:** `cd oee-platform/backend && make ci` (repo kökünden) → ruff + tüm pytest (yeni H4/H6/H7 + mevcut regression eşikleri) yeşil.
2. **Simülatör:** `cd simulator && .venv/Scripts/python.exe -m pytest -q` → 105 + yeni (hat varyasyonu, sensitivity) yeşil.
3. **Frontend:** `cd oee-platform/frontend && npm run lint && npm run test && npm run build` yeşil.
4. **H4 elle:** `multiseed_golden.json` + 10 seed dizini commit'li; `test_multiseed_parity` dağılım kapısı yeşil.
5. **H5 elle:** `docs/sensitivity_report.md` üretilmiş; etki tablosu beklenen yönde (doluluk↑→FILL↑).
6. **H6 görsel:** `docker compose up --build` → senaryo dropdown'ında anlatı görünür.
7. **H7 elle:** `POST /line/validate` geçerli line için `{"valid":true,"errors":[]}`, bozuk line için açık hata listesi.
8. **Firewall regression:** yeni analitik/üretim imzalarında `ground_truth` yok; mevcut firewall testi yeşil.

## Tamamlanınca

- Branch `feat/dalga-b-h4-h7` → PR → `main` (Dalga A PR'ı ile bağımsız).
- `docs/STATUS.md` güncelle: Hazırlık Dalga B tamam; sırada Dalga C (H8 utilization/takvim · H9 ops).
- Planı repoya kopyala (Task 0 Step 2).

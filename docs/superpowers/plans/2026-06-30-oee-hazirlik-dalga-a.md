# OEE Hazırlık — Dalga A (H1→H2→H3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Kanonik kayıt yeri:** Onaylanınca bu plan `oee-platform/docs/superpowers/plans/2026-06-30-oee-hazirlik-dalga-a.md` olarak repoya kopyalanacak.

## Context

18 Haziran'da yazılan `OEE_Hazirlik_Paketleri_Plani_H1-H9.md` (pilot/saha öncesi "derisk" işleri) hiç uygulanmadı; doğrulandı — `corrupt.py`, `adapter.py`, `confidence.py` vb. dosyaların hiçbiri yok. Bunun yerine 18 Haziran sonrası iş, frontend/tasarım netlik turlarına (PR #1–#3 + `feat/surface-computed-metrics`) gitti. Ürün çekirdeği (G1–G12 + Dalga 1–3) tamam ve testleri yeşil, ama **müşteri/saha verisi yok**.

Bu plan, H1-H9 dokümanının en yüksek getirili ilk hamlesini — **Dalga A: H1→H2→H3** — uygular. Amaç yeni "özellik" değil, ürünün sahada **çalışacağını** (kirli veri + adaptör) ve **güvenilir** olduğunu (belirsizlik/güven) müşteri olmadan kanıtlamak. Dalga B (H4–H7) ve C (H8–H9) bu plan bittikten sonra ayrı planlar olarak gelir.

**Goal:** Platforma kirli-veri dayanıklılığı (H1), konfigürasyonla ingest adaptörü (H2) ve belirsizlik/güven katmanı (H3) ekleyerek pilotu önceden derisk et.

**Architecture:** Mevcut katman ayrımını koru (`api → analytics/ingest → store(Repository) → duckdb`). H1 `loader.py`'nin var olan `try/except → LoadReport.add_rejection` desenini ham-CSV/yapısal hatalara genişletir. H2 yeni bir `adapter.py` + frozen-dataclass config'i, `POST /ingest`'in önüne opsiyonel bir dönüşüm adımı olarak ekler (sözleşme sabit kalır, H1 doğrulaması korunur). H3 `recommend.py`'de zaten var olan `_low/_high` + config-faktör desenini `cost.py`/`loss_tree.py`'ye ve yeni `confidence.py`'ye taşır.

**Tech Stack:** Python 3.11 · FastAPI · DuckDB · pydantic v2 · frozen dataclass config (yaml.safe_load) · pytest (`tmp_path` + gerçek DuckDB, mock yok) · React 19 + Vite (H3 panosu) · ruff.

## Global Constraints

- **Firewall korunur:** `ground_truth*` dosyaları ASLA ingest edilmez; `extract_loss_tree` / yeni analitik imzaları `ground_truth` parametresi ALMAZ (regression testi `inspect.signature` ile doğrular). Ground truth yalnız `tests/` tarafında (`conftest.baseline_truth_value/_cost`).
- **Katmanlar tek yönlü:** iş mantığı somut DuckDB'yi tanımaz; yalnız `Repository(Protocol)` üzerinden.
- **Config deseni:** her yeni ayar = `@dataclass(frozen=True)` + `load_*_config(path)` (`yaml.safe_load` + manuel `float/int` coercion, `.get(key, default)`); yol `AppConfig.*_config_path` üzerinden, env `OEE_*` (`config.py` deseni). Yeni profil = yeni YAML, kod değil.
- **Env deseni:** `os.environ.get("OEE_*", default)` lazy okuma (import'ta cache YOK; testler `monkeypatch.setenv`); feature flag'ler `enabled()` predicate'i ile (`auth.py` deseni).
- **Test/CI kapısı:** `make ci` (= `ruff check .` + `pytest -q`, repo kökünden) yeşil kalır. Mevcut regression sabitleri (`PARITY_TOL=0.01`, `LOSSLESS_MIN=0.95`, `INFERRED_MIN=0.85`) bozulmaz. ruff: `line-length=100`, `ignore=["E501"]`, `py311`.
- **Belirsizlik konvansiyonu:** nokta değer = iyimser/üst sınır; `*_low = nokta × low_factor`, `*_high = nokta × high_factor`; faktörler config'te (`recommend.py` / `RecommendConfig.recovery_low_factor/high_factor` örneği). H3 bu adlandırmayı (`_low/_high`) ve `Protocol` + varsayılan-impl modüler seam'ini birebir aynalar.
- **Yetersiz veri sinyali:** kısmi/boş pencerede `0`/`NaN` DÖNDÜRME; açık "yetersiz/güvenilmez veri" işareti döndür (H1 adım 4 → H3 köprüsü).
- Dil: kod İngilizce, yorum/docstring Türkçe (mevcut konvansiyon).

---

## Task 0: Branch kurulumu

**Files:** yok (git).

- [ ] **Step 1:** `main`'in güncel ve temiz olduğunu doğrula (`git -C oee-platform status`, `git log main --oneline -1` → `8e30f14`).
- [ ] **Step 2:** main'den yeni branch: `git -C oee-platform checkout main && git checkout -b feat/h1-dirty-data`.
- [ ] **Step 3:** Planı repoya kopyala: `oee-platform/docs/superpowers/plans/2026-06-30-oee-hazirlik-dalga-a.md`, commit `docs: H1-H3 (Dalga A) uygulama planı`.

---

# H1 — Kirli-veri dayanıklılığı

**Hedef:** Gerçek sahanın kusurlu verisini (eksik/bozuk/sıra-dışı) platform zarifçe ele alsın — bozuk satır raporlanır, sağlam satır yüklenir, sistem çökmez; kısmi/boş pencerede açık "yetersiz veri" sinyali. Pilotların en sık öldüğü yer.

### Task 1: `corrupt.py` — parametrik, seed'li kirlilik üreteci

**Files:**
- Create: `oee-platform/backend/tools/corrupt.py`
- Test: `oee-platform/backend/tests/test_corrupt_tool.py`

**Interfaces — Produces:**
```python
# her bozucu: temiz contract satır listesi (list[dict]) -> kirletilmiş list[dict], deterministik (seed)
def corrupt_rows(rows: list[dict], kind: str, seed: int = 42, rate: float = 0.1) -> list[dict]: ...
# kind ∈ {"missing_row","duplicate","out_of_order","clock_skew","partial_shift",
#         "unknown_reason","empty_required","type_corruption","negative_duration","disposition_violation"}
def main(argv: list[str] | None = None) -> int: ...   # CLI: --in <dir> --out <dir> --kind ... --seed ...
```
- Determinizm: `random.Random(seed)` (global `random` DEĞİL — `Math.random` benzeri kaçınma; modül `random` import edip `Random(seed)` instance). `events/production/orders` ayrı ayrı işlenir; her `kind` bağımsız bayrak.

- [ ] **Step 1:** Failing test yaz — `test_corrupt_tool.py`:
```python
from tools.corrupt import corrupt_rows

def test_out_of_order_is_deterministic():
    rows = [{"timestamp": f"2026-01-01T00:0{i}:00", "line_id": "L1", "event_type": "MICROSTOP"} for i in range(6)]
    a = corrupt_rows(rows, "out_of_order", seed=7)
    b = corrupt_rows(rows, "out_of_order", seed=7)
    assert a == b                          # aynı seed -> aynı çıktı
    assert [r["timestamp"] for r in a] != [r["timestamp"] for r in rows]  # sıra değişti
    assert sorted(r["timestamp"] for r in a) == sorted(r["timestamp"] for r in rows)  # küme korunur

def test_duplicate_adds_rows():
    rows = [{"timestamp": "2026-01-01T00:00:00", "line_id": "L1", "event_type": "LOAD", "carrier_id": "C1"}]
    out = corrupt_rows(rows, "duplicate", seed=1, rate=1.0)
    assert len(out) == 2 and out[0] == out[1]
```
- [ ] **Step 2:** Run → FAIL (`No module named tools.corrupt`). `pytest tests/test_corrupt_tool.py -v` (rootdir=backend; `tools` paketi import edilebilir olmalı → `tools/__init__.py` ekle).
- [ ] **Step 3:** `corrupt.py` impl — her `kind` için küçük saf fonksiyon (`_missing_row`, `_duplicate`, `_out_of_order`, ...) + dispatch dict; `corrupt_rows` seçer. CSV I/O sadece `main()` içinde (kullan: `csv.DictReader`/`DictWriter`).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `feat(h1): seed'li kirlilik üreteci (corrupt.py) + CLI`.

> Kirlilik türleri (sahadan beklenenler): eksik satır, duplicate, out-of-order timestamp, saat kayması/DST, kısmi vardiya (ilk/son dönem yarım), bilinmeyen `reason_code`/`event_type`, boş zorunlu alan, tip bozulması (sayı yerine metin), negatif/aşırı `duration`, `good+scrap != loaded` ihlali (G12 değişmezi).

### Task 2: Loader'ı yapısal/ham-CSV hatalarına karşı güçlendir

**Files:**
- Modify: `oee-platform/backend/app/ingest/loader.py` (`_read_csv`, `_load_events/_load_production/_load_orders`)
- Modify: `oee-platform/backend/app/ingest/report.py` (gerekiyorsa `add_rejection` kullanımı; yeni alan gerekmez)
- Test: `oee-platform/backend/tests/test_dirty_ingest.py`

**Interfaces — Consumes:** `load_csv_dir(path, repo) -> LoadReport`; `LoadReport.add_rejection(file, row, error)`; `report.to_dict()` → `{accepted, rejected_count, skipped, errors}`.

**Mevcut boşluk (keşiften):** bozuk satır zaten `(ValidationError, KeyError, ValueError)` ile yakalanıp `add_rejection`'a düşüyor; AMA `_read_csv` (ham parse/encoding) `try` DIŞINDA — yapısal bozukluk/encoding hatası tüm yüklemeyi düşürür.

- [ ] **Step 1:** Failing test — her kirlilik türü için bir vaka (`tmp_path` + `write_text`, gerçek DuckDB; `test_ingest_reject.py` deseni):
```python
def test_type_corruption_rejected_good_loaded(tmp_path):
    d = tmp_path / "data"; d.mkdir()
    (d / "events.csv").write_text(
        "timestamp,line_id,event_type,carrier_id,duration,reason_code,operator_entered_reason\n"
        "2026-01-01T00:00:00,L1,MICROSTOP,C1,30,jam,\n"
        "2026-01-01T00:01:00,L1,MICROSTOP,C2,NOTANUMBER,jam,\n")     # duration tip bozuk
    repo = _fresh_repo(tmp_path)
    rep = load_csv_dir(d, repo).to_dict()
    assert repo.count("events") == 1 and rep["rejected_count"] == 1

def test_malformed_csv_does_not_crash(tmp_path):
    d = tmp_path / "data"; d.mkdir()
    (d / "events.csv").write_text("timestamp,line_id\nthis,is,too,many,columns\n")
    repo = _fresh_repo(tmp_path)
    rep = load_csv_dir(d, repo).to_dict()    # çökmez; satır reddedilir
    assert rep["rejected_count"] >= 1
```
(`_fresh_repo` = `DuckDBRepository(str(tmp/"t.duckdb"))` + connect + init_schema; conftest helper'a çıkar.)
- [ ] **Step 2:** Run → en az `test_malformed_csv_does_not_crash` FAIL (ham parse hatası dışarı sızar) / negatif-duration & disposition vakaları yeşil olabilir (zaten kapsanıyor — varsa not düş).
- [ ] **Step 3:** Impl — `_read_csv`'i satır-bazlı sağlamlaştır: malformed satırı (örn. `csv.Error`, kolon-sayısı uyumsuzluğu) yakala, o satırı `add_rejection`'a yaz, döngüyü sürdür; encoding'i `utf-8-sig` + `errors="replace"` aç. Negatif/aşırı `duration` için contract model'e (`EventRow`) `@field_validator` ekle (negatif → ValueError → red). Bunları minimal tut; YAGNI.
- [ ] **Step 4:** Run → PASS; `make ci` yeşil (mevcut testler kırılmasın).
- [ ] **Step 5:** Commit: `feat(h1): loader ham-CSV/yapısal kirlilikte zarif-bozulma`.

### Task 3: Kirli fixture seti üret + commit'le (üretici ile)

**Files:**
- Create: `oee-platform/backend/tests/fixtures/dirty/<kind>/{events,production,orders}.csv` (her tür bir alt-dizin)
- Modify: `oee-platform/backend/tests/conftest.py` (`DIRTY = FIXTURES / "dirty"` + `_fresh_repo` helper)
- Test: `oee-platform/backend/tests/test_dirty_ingest.py` (Task 2'yi fixture-tabanlı parametrize ile genişlet)

- [ ] **Step 1:** `tools/corrupt.py` ile `fixtures/baseline/` (veya `lossless/`) üzerinden her `kind` için kirli varyant üret; `dirty/<kind>/` altına yaz.
- [ ] **Step 2:** Parametrize test: `@pytest.mark.parametrize("kind", KINDS)` — her dizin için `load_csv_dir` çökmeden çalışır, `accepted` > 0 (en az bir sağlam satır), `rejected_count` beklenen türde ≥ 1. (DST/clock_skew & duplicate için: çökme yok + idempotency korunur.)
- [ ] **Step 3:** Run → PASS.
- [ ] **Step 4:** Commit: `test(h1): kirli fixture seti + her tür için ingest dayanıklılık testi`.

### Task 4: Analitik katmanı — kısmi/boş pencerede "yetersiz veri" sinyali

**Files:**
- Modify: `oee-platform/backend/app/analytics/data_quality.py` (`sufficiency_flag` veya `coverage` genişlet)
- Modify (gerekiyorsa): `oee-platform/backend/app/analytics/oee.py`, `loss_tree.py` (boş `events/production` → çökme yerine açık işaret)
- Test: `oee-platform/backend/tests/test_dirty_compute.py`, `tests/test_out_of_order.py`

**Interfaces — Produces:** `data_quality.entry_coverage(events)` zaten `{"microstop_entry_coverage": float}` döndürüyor. Genişlet:
```python
def coverage(events: list[dict], production: list[dict]) -> dict:
    # {"microstop_entry_coverage": float, "event_count": int, "span_min": float,
    #  "sufficient": bool}   # sufficient=False -> "yetersiz veri" (eşik config/sabit)
```

- [ ] **Step 1:** Failing test — `test_dirty_compute.py`: boş/seyrek pencerede `compute_oee([], [], line)` çökmeden makul sonuç (ör. `oee==0.0` AMA `coverage(...)["sufficient"] is False`); kirli baseline'da `extract_loss_tree` çökmez. `test_out_of_order.py`: out-of-order + duplicate timestamp'te `availability_from_events` span ve `union_length` doğru (sıralama/union dedup'a dayanıklı).
- [ ] **Step 2:** Run → FAIL (`sufficient` yok / boş girişte çökme).
- [ ] **Step 3:** Impl — `coverage` eşik mantığı (event_count & span tabanlı; eşik sabit, gerekirse config); `oee.py`/`loss_tree.py` boş girişte guard. Out-of-order için `availability_from_events` zaten `union_length` kullanıyor; testle doğrula, gerekiyorsa intervalleri sırala.
- [ ] **Step 4:** Run → PASS; `make ci` yeşil.
- [ ] **Step 5:** Commit: `feat(h1): kısmi/boş pencerede yetersiz-veri sinyali + out-of-order doğruluğu`.

**H1 Başarı kriteri:** Her kirlilik türü için sağlam veri yükleniyor, bozuk satır raporlanıyor, sistem çökmüyor; kirli baseline'da OEE/kayıp ağacı ya makul sonuç ya açık "yetersiz/güvenilmez veri" sinyali; tüm testler + CI yeşil.

---

# H2 — Konfigürasyonla ingest adaptörü

**Hedef:** Tesisin verebildiği ham formatı (PLC/SCADA export, sayaç logu, MES/ERP CSV) **konfigürasyonla** sözleşme CSV'sine çevir. Sözleşme sabit; iş "sahanın dili"ne köprü. Yeni profil = yeni YAML, kod değil.

### Task 5: `adapter.py` + `AdapterConfig` + `load_adapter_config`

**Files:**
- Create: `oee-platform/backend/app/ingest/adapter.py`
- Modify: `oee-platform/backend/app/config.py` (`AdapterConfig` dataclass + `load_adapter_config(path)`; `AppConfig`'e gerek YOK — adapter yolu runtime parametresi)
- Create: `oee-platform/config/adapters/generic_plant.yaml`
- Create: `oee-platform/backend/tests/fixtures/raw/{generic_plant_events,...}.csv` (sözleşme-dışı örnek ham CSV)
- Test: `oee-platform/backend/tests/test_adapter_mapping.py`, `tests/test_adapter_errors.py`

**Interfaces — Produces:**
```python
@dataclass(frozen=True)
class AdapterConfig:
    column_map: dict[str, str]            # ham_kolon -> sözleşme_kolon
    timestamp_format: str | None          # strptime fmt; None -> ISO
    timezone: str | None                  # IANA, ör. "Europe/Istanbul" -> UTC normalize
    duration_unit: str                    # "s" | "min"  (sn -> sn sabit; "min" -> *60)
    reason_map: dict[str, str]            # ham etiket -> standart reason_code
    event_type_rule: dict[str, str]       # ham değer -> EventType
    defaults: dict[str, str]              # eksik zorunlu alan için varsayılan
def load_adapter_config(path: str) -> AdapterConfig

def apply_mapping(raw_rows: list[dict], mapping: AdapterConfig) -> list[dict]:
    # ham satırları SÖZLEŞME satırlarına çevirir (kolon, zaman+tz, süre birimi, reason, event_type, default)
    # eşlenemeyen değer / eksik zorunlu kolon -> AdapterError (açık, eyleme dönük mesaj)
class AdapterError(ValueError): ...
```
Konvansiyon: `config.py`'deki frozen-dataclass + `yaml.safe_load` + manuel coercion. tz dönüşümü stdlib `zoneinfo`.

- [ ] **Step 1:** Failing test — `test_adapter_mapping.py`:
```python
def test_apply_mapping_basic():
    cfg = load_adapter_config(str(ADAPTERS / "generic_plant.yaml"))
    raw = [{"ts": "01/01/2026 09:00:00", "machine": "L1", "evt": "STOP", "dur_min": "2", "cause": "Sıkışma"}]
    out = apply_mapping(raw, cfg)
    assert out[0]["event_type"] == "MICROSTOP"        # event_type_rule: STOP->MICROSTOP
    assert out[0]["duration"] == 120                  # dur_min "2" -> 120 sn
    assert out[0]["reason_code"] == "jam"             # reason_map: Sıkışma->jam
    assert out[0]["line_id"] == "L1"
    assert out[0]["timestamp"].startswith("2026-01-01T")
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Impl `apply_mapping` + `load_adapter_config`; `generic_plant.yaml` + `fixtures/raw/` örnek ham CSV.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Error testleri (`test_adapter_errors.py`): eksik zorunlu kolon → `AdapterError` açık mesaj; eşlenemeyen reason/event_type → açık hata (sessiz yanlış DEĞİL). Run → PASS.
- [ ] **Step 6:** Commit: `feat(h2): konfigürasyonla ingest adaptörü (apply_mapping + AdapterConfig)`.

### Task 6: `POST /ingest`'e opsiyonel `adapter` parametresi + uçtan uca test

**Files:**
- Modify: `oee-platform/backend/app/api/ingest_routes.py` (`IngestRequest.adapter: str | None = None`)
- Test: `oee-platform/backend/tests/test_adapter_end_to_end.py`

**Interfaces — Consumes:** `apply_mapping`, `load_adapter_config`, `load_csv_dir` (H1 doğrulaması korunur).

Akış: `adapter` verilirse → ham CSV'leri oku → `apply_mapping` → geçici dizine sözleşme CSV'si yaz → `load_csv_dir(temp_dir, repo)` (mevcut H1 doğrulamasından geçer). Adapter `None` → bugünkü davranış değişmez.

- [ ] **Step 1:** Failing test — `test_adapter_end_to_end.py` (TestClient + `monkeypatch.setenv("OEE_DUCKDB_PATH", ...)`):
```python
def test_ingest_with_adapter_then_oee(tmp_path, monkeypatch):
    monkeypatch.setenv("OEE_DUCKDB_PATH", str(tmp_path / "api.duckdb"))
    with TestClient(app) as client:
        r = client.post("/ingest", json={"path": str(RAW_DIR), "adapter": "generic_plant"})
        assert r.status_code == 200 and r.json()["accepted"]["events"] > 0
        assert client.get("/oee").status_code == 200
```
- [ ] **Step 2:** Run → FAIL (`adapter` yok sayılır / 422).
- [ ] **Step 3:** Impl route: adapter çözümleme (`config/adapters/<name>.yaml`), ham oku → adapt → temp dir → `load_csv_dir`. Bilinmeyen profil → HTTP 400 açık mesaj.
- [ ] **Step 4:** Run → PASS; `make ci` yeşil.
- [ ] **Step 5:** Commit: `feat(h2): POST /ingest?adapter=<profil> uçtan uca + hata yolları`.

**H2 Başarı kriteri:** Örnek ham CSV `generic_plant` profiliyle sözleşmeye çevrilip sorunsuz ingest, `/oee` çalışıyor; eksik/eşlenemeyen alan açık hata; yeni profil yalnız YAML.

---

# H3 — Belirsizlik/güven + öz-teşhis

**Hedef:** Gizli kayıp çıkarımına (FILL/SPEED) sahada ground-truth olmadan **güven** kazandır: nokta değer yerine güven aralığı (`value_low/high`, `tl_low/high`) + veri-yeterlilik skoru. "Sessizce yanlış sayı" yerine "ne kadar emin".

### Task 7: `confidence.py` — data_sufficiency + bant üreteci

**Files:**
- Create: `oee-platform/backend/app/analytics/confidence.py`
- Modify: `oee-platform/config/recommend.yaml` veya yeni `config/confidence.yaml` (faktörler) + `config.py` `load_confidence_config`
- Test: `oee-platform/backend/tests/test_confidence_sufficiency.py`, `tests/test_confidence_bands.py`

**Interfaces — Produces:**
```python
class BandEstimator(Protocol):                 # recommend.GainEstimator deseni
    def band(self, channel: str, value: float, sufficiency: float) -> tuple[float, float]: ...

@dataclass(frozen=True)
class ConfidenceConfig:
    low_factor: float; high_factor: float; sufficiency_threshold: float

def data_sufficiency(events: list[dict], production: list[dict], line: LineDefinition) -> float:
    # 0..1 — olay yoğunluğu, kapsanan süre, eksik-alan oranı, microstop giriş kapsamı (G10) sinyallerinden
def band(channel: str, value: float, sufficiency: float, cfg: ConfidenceConfig) -> tuple[float, float]:
    # low <= value <= high; düşük sufficiency -> daha geniş bant
```
- **Firewall:** `data_sufficiency`/`band` `ground_truth` ALMAZ (regression `inspect.signature` testi ekle).

- [ ] **Step 1:** Failing test — `test_confidence_sufficiency.py`: bol/yoğun olay → skor yüksek (≥0.8); seyrek/kısmi → düşük (≤0.4). `test_confidence_bands.py`: `low <= point <= high`; **baseline'da çıkarım kanallarının (FILL/SPEED) bandı `conftest.baseline_truth_value(cat)` gerçeğini KAPSAR** (`low ≤ gerçek ≤ high`) — bu kritik kabul kriteri.
- [ ] **Step 2:** Run → FAIL (`confidence` modülü yok).
- [ ] **Step 3:** Impl — `data_sufficiency` gözlemlenebilir sinyallerden ağırlıklı 0..1; `band` = `value × low_factor / high_factor`, bant genişliği `sufficiency`'e göre ayarlı (şeffaf, varsayım-tabanlı; aşırı mühendislik YOK). Faktörler config'ten.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `feat(h3): confidence.py — data_sufficiency + çıkarım bandı`.

### Task 8: `loss_tree`/`cost`/`recommend` belirsizliği taşısın

**Files:**
- Modify: `oee-platform/backend/app/analytics/cost.py` (`to_tl` → her kategoriye `tl_low/high` + `confidence`)
- Modify: `oee-platform/backend/app/analytics/loss_tree.py` (gerekiyorsa `value_low/high` — çıkarım kanalları için)
- Modify: `oee-platform/backend/app/analytics/recommend.py` (düşük güvenli kalemde `low_confidence: bool` + uyarı)
- Test: `oee-platform/backend/tests/test_confidence_propagation.py`

**Interfaces — Consumes:** `band(...)`, `data_sufficiency(...)`, mevcut `to_tl` çıktı şekli `{categories:[{category,axis,value,tl,kind}], total_tl}`. **Produces:** `to_tl` kategorisine ek alanlar `tl_low`, `tl_high`, `confidence` (görünür kanallarda `confidence=1.0`, bant=nokta; çıkarım kanallarında bant + skor).

- [ ] **Step 1:** Failing test — `test_confidence_propagation.py`: `to_tl(...)` her kategoride `tl_low <= tl <= tl_high`; çıkarım kanalı (FILL/SPEED) `confidence < 1`, görünür kanal `confidence == 1`; `total_tl` değişmez (nokta toplam korunur). recommend: düşük güvenli kalem `low_confidence=True`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Impl — `cost.to_tl` içine `band` + `data_sufficiency` enjekte et (mevcut imza geriye uyumlu: yeni `confidence_cfg` opsiyonel param, route besler). `recommend.generate_recommendations` düşük güveni işaretler.
- [ ] **Step 4:** Run → PASS; `make ci` + regression yeşil (`total_tl`/parite değişmedi).
- [ ] **Step 5:** Commit: `feat(h3): cost/recommend belirsizlik bandı + düşük-güven işareti taşıma`.

### Task 9: API uçları belirsizliği yüzeye çıkarsın

**Files:**
- Modify: `oee-platform/backend/app/api/loss_tree_routes.py` (`/loss-tree/cost` → kategoride `tl_low/high`, `confidence`; route `confidence` config'i yükler ve besler)
- Modify: `oee-platform/backend/app/api/recommend_routes.py` (low_confidence alanı zaten dict'te)
- Test: `oee-platform/backend/tests/test_cost_endpoint_confidence.py`

- [ ] **Step 1:** Failing endpoint test: `GET /loss-tree/cost` JSON'unda her kategoride `tl_low/tl_high/confidence` var; çıkarım kanalında `confidence < 1`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Route'a `load_confidence_config(...)` + besle (analitik route deseni: per-request config reload).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `feat(h3): /loss-tree/cost belirsizlik alanları`.

### Task 10: Pano — aralık + güven rozeti

**Files:**
- Modify: `oee-platform/frontend/src/...` (TL Pareto / kayıp ağacı bileşeni: bant gösterimi + "güven" rozeti; düşük güvende soluk/uyarı)
- Test: `oee-platform/frontend/src/...test` (vitest smoke: rozet render olur, low-confidence görsel ayrım var)

**Not:** PRODUCT.md/DESIGN.md yönü korunur — cyan=etkileşim; yeşil/mor/mercan = veri kanalı; rozet düşük-doygunluk, neon yok. Düşük güven = soluk + küçük uyarı ikonu, renk-körü güvenli (etiket de taşır).

- [ ] **Step 1:** Failing vitest smoke: düşük-güvenli kategori için "düşük güven" rozeti/uyarısı DOM'da.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Bileşeni `tl_low/high` + `confidence` tüketecek şekilde güncelle; aralık (ör. ince bar) + rozet.
- [ ] **Step 4:** Run → PASS (`npm run test`); `npm run lint` + `npm run build` yeşil.
- [ ] **Step 5:** Commit: `feat(h3): pano belirsizlik aralığı + güven rozeti`.

**H3 Başarı kriteri:** Baseline'da çıkarım kanallarının güven aralığı ground_truth'u **kapsıyor** (low ≤ gerçek ≤ high); seyrek/kısmi veride yeterlilik skoru düşüyor + kanal "düşük güven"; cost/recommend tutarlı taşıyor; pano gösteriyor; tüm testler + CI yeşil.

---

## Doğrulama (uçtan uca)

1. **Birim/entegrasyon:** repo kökünden `make ci` → ruff temiz + tüm pytest (mevcut + yeni H1/H2/H3) yeşil; regression sabitleri (`PARITY_TOL/LOSSLESS_MIN/INFERRED_MIN`) korunuyor.
2. **Frontend:** `cd frontend && npm run lint && npm run test && npm run build` yeşil.
3. **H1 elle:** `python -m tools.corrupt --in tests/fixtures/baseline --out /tmp/dirty --kind type_corruption`; `POST /ingest {"path": "/tmp/dirty"}` → `rejected_count > 0`, `accepted.events > 0`, sunucu ayakta.
4. **H2 elle:** `POST /ingest {"path": "tests/fixtures/raw", "adapter": "generic_plant"}` → 200, sonra `GET /oee` makul sonuç.
5. **H3 elle/görsel:** `docker compose up --build` → pano TL Pareto'sunda çıkarım kanallarında aralık + "düşük güven" rozeti görünür; `GET /loss-tree/cost` JSON'unda `tl_low/high/confidence`.
6. **Firewall regression:** `data_sufficiency`/`band`/`apply_mapping` imzalarında `ground_truth` yok (yeni `inspect.signature` assert'leri yeşil).

## Tamamlanınca

- Her paket kendi commit setiyle; `feat/h1-dirty-data` (veya H2/H3 için ayrı branch'ler) → PR(ler) → `main`.
- `docs/STATUS.md` güncelle: H1–H3 tamam; sırada Dalga B (H4–H7).
- Bu plan dosyasını repoya kopyalamayı unutma (Task 0 Step 3).

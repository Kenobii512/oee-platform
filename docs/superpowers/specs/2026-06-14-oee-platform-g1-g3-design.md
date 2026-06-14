# OEE Platform G1–G3 — Tasarım Spec'i

**Tarih:** 2026-06-14
**Kapsam:** `oee-platform/` reposunun ilk üç görevi (G1 iskelet + sözleşme, G2 ingest, G3 OEE motoru).
**Kaynak brief:** `Claude_Code_Gorevleri_G1-G3.md`. Bu spec, brief'i + brainstorming'de
alınan kararları sabitler. Brief ile çelişen bir şey yoktur; yalnız brief'te açık
bırakılan noktalar netleştirilmiştir.

---

## 1. Amaç ve ilkeler

Bir kaplama hattı için OEE/verimlilik platformunun çalışan iskeletini kurmak, genel
CSV'leri doğrulayıp DuckDB'ye yüklemek ve OEE'yi **yalnızca genel (public) veriden**
hesaplamak. Simülatör yalnız test verisi ve referans üretir; platform onun iç durumunu
bilmez.

Değişmez ilkeler:
- **Şema kutsaldır:** Platform, verinin simülatörden mi sahadan mı geldiğini bilmez.
  Şema simülatörün çıktı şemasıyla birebir ama platformda **bağımsız sözleşme** olarak
  tanımlanır.
- **Firewall:** `ground_truth.csv` ASLA ingest edilmez. Loader dosyayı **açmadan** atlar.
- **Tek doğruluk kaynağı:** OEE/kayıp mantığı platformda tek serviste toplanır;
  simülatörün `metrics.py`/`accuracy.py`'si yalnız referans/regresyon içindir.
- **Determinizm & test:** Test olmadan görev tamam sayılmaz. Birim maliyet/oran gibi
  sabitler config'te, kodda gömülü değil.
- **DuckDB→Postgres:** Veri erişimi ince bir `Repository` arayüzü arkasında; ileride tek
  dosyadan Postgres'e geçilebilir.

---

## 2. Mimari ve katmanlar

```
oee-platform/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + /health
│   │   ├── config.py           # env + line_default.yaml -> AppConfig, LineDefinition
│   │   ├── api/
│   │   │   ├── ingest_routes.py # POST /ingest
│   │   │   └── oee_routes.py    # GET /oee
│   │   ├── models/
│   │   │   └── contract.py      # EventRow, ProductionRow, OrderRow, EventType, LineDefinition
│   │   ├── store/
│   │   │   ├── repository.py    # Repository Protocol (soyut)
│   │   │   └── duckdb_repo.py   # DuckDBRepository (şema + idempotent upsert + sorgular)
│   │   ├── ingest/
│   │   │   ├── loader.py        # load_csv_dir(path) -> LoadReport
│   │   │   └── report.py        # LoadReport
│   │   └── analytics/
│   │       └── oee.py           # compute_oee(period) -> OeeResult
│   ├── tests/
│   │   ├── fixtures/            # simülatörden üretilen seed-42 CSV setleri
│   │   └── test_*.py
│   ├── requirements.txt
│   └── Dockerfile
├── config/
│   └── line_default.yaml        # simülatörden kopyalanan hat tanımı (referans)
├── docs/{adr/0001-mimari.md, data-contract.md}
├── docker-compose.yml
├── .gitignore
└── README.md
```

**Bağımlılık yönü tek yönlü:** `api → analytics/ingest → store(Repository) → duckdb`.
İş mantığı (`analytics/oee.py`, `ingest/loader.py`) somut DuckDB'yi import etmez; yalnız
`Repository` arayüzünden satır/dict alır. DuckDB→Postgres geçişi tek dosyada
(`duckdb_repo.py`) izole kalır.

---

## 3. Veri sözleşmesi (G1)

Kaynak: `simulator/output/*.csv` formatı. Üç genel dosya platforma girer; `ground_truth.csv`
girmez.

**events.csv:** `timestamp` (ISO datetime), `line_id` (str), `station_id` (str/boş),
`event_type` (enum), `duration` (float dk), `reason_code` (str/boş),
`operator_entered_reason` (str/boş), `operator_entry_ts` (datetime/boş).

`EventType` enum (9 değer): `LOAD, PROCESS, MOVE, UNLOAD, QC, OVER_RESIDENCE, DOWNTIME,
MICROSTOP, STRIP`.

**production.csv:** `carrier_id` (str), `order_id` (str), `loaded_qty` (int),
`good_count` (int), `redo_count` (int), `scrap_count` (int).
Değişmez: `good_count + scrap_count == loaded_qty` (pydantic validator). `redo_count` ayrı
rework hacmidir, bölünmeye dahil değil.

**orders.csv:** `order_id`, `product_id`, `target_cycle` (float), `planned_qty` (int).

Boş olabilen alanlar `Optional`. Modeller `models/contract.py`'de pydantic ile.

### Hat tanımı (LineDefinition)

`config/line_default.yaml` formatından okunur. İçerir:
- **tanks:** sıralı liste; her biri `id, name, time_min, time_max, capacity, bottleneck,
  max_hold_min`.
- **carrier_capacity:** iş emri başına askı kapasitesi (`{order_id: carrier_qty}`).
  YAML'ın `orders[].carrier_qty` alanından doldurulur. **Quality paydası için
  master-data'dır** (bkz. §5). Tanımsızsa `None` → çıkarım fallback'i.

> **Not (firewall):** `carrier_capacity` ground-truth değildir; sahada da bilinen
> mühendislik master-data'sıdır (raf nominal kapasitesi). Hat tanımı config'inden okunması
> meşrudur; ingest edilen CSV'lerde olması gerekmez.

---

## 4. Ingest + depolama (G2)

`ingest/loader.py::load_csv_dir(path) -> LoadReport`:
1. Klasördeki `events.csv`, `production.csv`, `orders.csv` dosyalarını işler.
2. Her satırı ilgili pydantic modeliyle doğrular. Geçersizler `LoadReport`'a (sebep + satır
   no), geçerliler DuckDB'ye.
3. `good_count + scrap_count != loaded_qty` ihlali = ret.
4. **Firewall:** adı `ground_truth` ile başlayan dosya **açılmadan** atlanır; raporda
   `firewall: skipped` işaretlenir.

`POST /ingest` (yol gövdede) → `LoadReport` (kabul/ret/atlanan sayıları + ilk N hata).

### Idempotency (tabloya göre hibrit)

| Tablo | Anahtar | Çatışma davranışı | Gerekçe |
|---|---|---|---|
| production | PK `carrier_id` | `ON CONFLICT DO UPDATE` | Kararlı doğal anahtar; düzeltme güvenli ve anlamlı |
| orders | PK `order_id` | `ON CONFLICT DO UPDATE` | Aynı |
| events | `(source_file, row_ordinal)` | `ON CONFLICT DO NOTHING` | Doğal anahtar yok; konumsal vekil. Özdeş olaylar korunur, süre toplamları doğru kalır |

events'te `DO NOTHING` bilinçlidir: konumsal anahtarda `DO UPDATE`, upstream satır
ekler/çıkarırsa yanlış mantıksal olayı sessizce ezerdi; event-log düzeltmesi zaten nadirdir.
İçerik-hash'i yaklaşımı reddedildi çünkü meşru özdeş iki olayı yutup süre toplamlarını
eksiltir (paralel istasyonlu gerçek hat senaryosu).

`events` tablosuna `source_file`, `row_ordinal` sütunları eklenir (analitik bunları yok
sayar).

---

## 5. OEE motoru (G3)

`analytics/oee.py::compute_oee(period) -> OeeResult`. Bir dönem `[from, to]` için yalnız
events + production + hat tanımından hesaplar. Tanımlar simülatör `src/metrics.py` ile
**birebir**:

- **Availability** = `(span − union(DOWNTIME ∪ MICROSTOP)) / span`.
  `span` = `max(timestamp + duration) − min(timestamp)` (dakika). Aralık birleşimi
  `metrics.py::_union_length` ile aynı algoritma (örtüşen/iç içe duruşlar bir kez sayılır).
- **Performance** = `(askı_sayısı × Σ_tank (time_min+time_max)/2) / Σ PROCESS_duration`.
  `askı_sayısı` = production satır sayısı; nominal tam-geçiş hat tanımından.
- **Quality** = `Σ good_count / Σ intended`.
  `intended` = **Seçenek B**: hat tanımındaki `carrier_capacity[order_id]` (master-data).
  Kapasite tanımsızsa **fallback (Seçenek A)**: iş emri başına `max(loaded_qty)` nominal
  kabul edilir (`accuracy.py::extract_loss_tree` deseni). Lossless ve baseline (config'li)
  durumda B yolu metrics.py ile birebir eşleşir.
- **OEE** = A × P × Q. Hepsi `_clamp01` (0–1).
- **Utilization (ayrı, OEE'yi değiştirmez):** `planned_downtime_min` = calendar config'teki
  `planned_maintenance` (+ vardiya dışı + molalar) penceresi `[from, to]` ile kesişimi.
  `OeeResult`'ta ayrı alan. `metrics.py`'de karşılığı yoktur → **parite testine girmez**.

`GET /oee?from=...&to=...` → `OeeResult` (A, P, Q, OEE, utilization, planned_downtime_min).

---

## 6. Test stratejisi

Golden fixture'lar simülatörün `.venv`'iyle `seed=42` çalıştırılarak üretilir
(`backend/tests/fixtures/`): bir **lossless** set ve bir **baseline** set (senaryo dosyası).
Aynı çalıştırmadan `metrics.py`'nin A/P/Q/OEE değerleri alınıp `test_oee_baseline`'a sabit
beklenen olarak gömülür.

- **G1:** `test_health` (`GET /health` → 200, `{"status":"ok"}`),
  `test_contract` (geçerli satır kabul; bozuk `event_type` / eksik zorunlu alan /
  `good+scrap != loaded` reddi).
- **G2:** `test_ingest_ok` (set hatasız yüklenir, satır sayıları eşleşir),
  `test_ingest_reject` (bozuk satır reddi + rapora yazılır),
  `test_idempotent` (aynı dosya 2× → satır sayısı sabit),
  `test_no_ground_truth` (ground_truth klasörde olsa bile yüklenmez).
- **G3:** `test_oee_lossless` (lossless sette OEE ≥ %95),
  `test_oee_baseline` (seed 42 baseline, platform A/P/Q/OEE ↔ metrics.py ±%1),
  `test_oee_defs` (A/P/Q birim testleri; özellikle eşzamanlı/iç içe duruş birleşimi bir kez).

---

## 7. Kapsam dışı (bu görevde YOK)

- Kayıp ağacı çıkarımı (G4), öneri motoru (G9), TL maliyetlendirme (G11), arayüz/pano (G5),
  regresyon düzeneği (G6).
- k8s, çok-kiracılık, what-if motoru.
- events için delta-append / farklı-dosya-adıyla yeniden yükleme (idempotency yalnız "aynı
  dosya 2×" garantisi verir).

---

## 8. Çalışma sırası

`G1 → G2 → G3` sıralı; her biri öncekine yaslanır. Her görev sonunda `pytest` yeşil olmadan
sonrakine geçilmez. G1 ayrıca `docker-compose up` ile doğrulanır.

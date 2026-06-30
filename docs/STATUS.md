# OEE Platform — Proje Durumu (planlama özeti)

**Güncelleme:** 2026-06-30 · **Repo:** `Kenobii512/oee-platform` (private) · **Test (entegre main):** backend + frontend vitest 8/8 + simülatör 115/115 yeşil
**Yığın:** Python 3.11 · FastAPI · DuckDB · Docker · **pano: React 19 + Vite (SPA)** (eski Jinja `/legacy`'de) · SSE replay

Bu doküman, bir sonraki planlama oturumu için "ne bitti, ne nasıl çalışıyor, sırada ne var"
özetidir. Ayrıntılı tasarım/plan: `docs/superpowers/specs` ve `docs/superpowers/plans`.

---

## Tamamlanan görevler (G1–G5 · Dalga 1: G6·G11·G9 · Dalga 2: G8·GR·G7 · Dalga 3: G12·G4.1·G10·Perf-UI)

| Görev | Teslim | Durum |
|------|--------|-------|
| **G1** | Repo iskeleti, veri sözleşmesi (pydantic), `Repository` arayüzü, `/health`, ADR + data-contract | ✓ |
| **G2** | CSV ingest (doğrulama + firewall + idempotency), DuckDB depo, `POST /ingest` | ✓ |
| **G3** | OEE motoru (A/P/Q/OEE) — yalnız public veriden; simülatör `metrics.py` ile **birebir** parite | ✓ |
| **G4** | Kayıp ağacı (6 kategori, gizli kanal çıkarımı), `GET /loss-tree` | ✓ |
| **G5** | Minimal pano (KPI, şelale, kayıp ağacı, trend, veri-kalite) + premium redesign | ✓ |
| **G6** | Regresyon/CI kapısı (GitHub Actions: ruff + pytest), `test_regression_contract.py` açık eşik sabitleri | ✓ |
| **G11** | TL (maliyet) lensi: `config/costs.yaml` + `analytics/cost.py`, `GET /loss-tree/cost`, pano TL Pareto'su | ✓ |
| **G9** | Kural tabanlı öneri motoru: `analytics/recommend.py` (modüler `GainEstimator`), `GET /recommendations`, pano "Öneriler" | ✓ |
| **G8** | Senaryo kütüphanesi: 6 demo senaryosu (golden fixture), `GET /scenarios` + `POST /scenarios/{id}/activate`, pano seçici; **doğal-eksen** kalibrasyon kapısı | ✓ |
| **GR** | Pano React 19 + Vite'a taşındı (JSON sözleşmesi değişmedi); FastAPI SPA'yı `/`'ta sunar, Jinja `/legacy`'de; çok aşamalı Docker; CI frontend job | ✓ |
| **G7** | Hızlandırılmış replay: `analytics/replay.py` (sanal saat + artımlı snapshot), `GET /replay/stream` (SSE), canlı React Replay görünümü (oynat/duraklat/hız); final snapshot statik ile birebir | ✓ |
| **G12** | Model revizyonu: **no-scrap** (spec-dışı parça sıyrılıp iyi olana dek tekrar kaplanır) + **çift kalite** (OEE Q = ilk-geçiş `(loaded−redo)/loaded`; ayrı `final_yield` = `good/loaded` ≈%100). Kategoriler **6→5** (QUALITY_SCRAP kalktı). `redo_count` = redo'dan geçen ayrık parça. Pano KPI çift kalite. 8 golden yeniden üretildi; parite eşikleri yeniden kalibre (REDO geniş bant: ayrık-parça vs döngü-hacmi) | ✓ |
| **G4.1** | Dönem-doğru üretim atfı: `events.csv`'ye **`carrier_id`**; `fetch_production(frm,to)` askıyı kendi olaylarının en geç zaman damgasına göre pencereye bağlar → trend/replay'de **P/Q pencere-doğru** değişir (eskiden dönem-sabit) | ✓ |
| **G10** | Operatör = **yalnız microstop**: senaryo `operator.channels` sadeleşti (DOWNTIME kalktı; duruş nedeni sistemce `reason_code`). `data_quality` yalnız `microstop_entry_coverage`. Pano "tek manuel girdi = mikro duruş; gerisi sistemce" anlatısı (Excel/manuel takibe karşı satış argümanı) | ✓ |
| **Perf-UI** | Görünürlük: trend grafiğine **Performance + Quality(ilk-geçiş) + nihai verim** çizgileri (G4.1 ile pencere-doğru); replay'e **Performance** KPI; öneri **kazanç aralığı** (`estimated_gain_tl_low/high`) + toplam "üst sınır; örtüşebilir" çekincesi | ✓ |

## API yüzeyi (mevcut)

```
GET  /health                          -> {"status":"ok"}
POST /ingest        {"path": "..."}    -> LoadReport (kabul/ret/atlanan + ilk N hata)
GET  /oee?from=&to=                    -> {availability, performance, quality(=ilk-geçiş), oee, utilization, planned_downtime_min, final_yield}
GET  /loss-tree?from=&to=              -> {categories:[{category, axis, value, kind}]}  (5 kategori; no-scrap)
GET  /loss-tree/cost?from=&to=         -> {categories:[{category, axis, value, tl, kind}], total_tl}  (5 kategori, TL azalan)
GET  /recommendations?from=&to=        -> {recommendations:[{category, tl, estimated_gain_tl, estimated_gain_tl_low, estimated_gain_tl_high, title, action, assumption, ...}], total_estimated_gain_tl}
GET  /oee/trend?bucket=day|week        -> [{period, availability, performance, quality, final_yield, oee}]  (P/Q pencere-doğru)
GET  /data-quality/summary             -> {microstop_entry_coverage}  (G10: tek manuel girdi)
GET  /scenarios                        -> {scenarios:[{id, title, description, expected_top_loss, data_dir}]}  (6 demo)
POST /scenarios/{id}/activate          -> {activated, ingest}  (repo.reset() + o senaryoyu ingest)
GET  /replay/stream?scenario=&speed=&steps=  -> SSE: büyüyen 'şimdiye kadar' snapshot'ları (oee, cost, gain, event_count)
GET  /                                 -> React SPA (build varsa) ya da Jinja fallback (HTML)
GET  /legacy                           -> Jinja panosu (her zaman; SPA fallback)
```

## Mimari & sabit kararlar

- **Katmanlar tek yönlü:** `api → analytics/ingest → store(Repository) → duckdb`. İş mantığı
  somut DuckDB'yi tanımaz → DuckDB→Postgres geçişi tek dosyada izole.
- **Firewall:** `ground_truth.csv` ASLA ingest edilmez (loader dosyayı açmadan atlar);
  `extract_loss_tree` imzası `ground_truth` ALMAZ. Gerçek yalnız doğrulama testlerinde.
- **Tek doğruluk kaynağı:** OEE/kayıp mantığı platformda; simülatör `metrics.py`/`accuracy.py`
  yalnız referans/regresyon. Baseline (seed 42) OEE ve kayıp ağacı simülatörle birebir doğrulandı.
- **Quality paydası (Seçenek B):** hat tanımı askı kapasitesi (master-data); tanımsızsa iş emri
  başına `max(loaded_qty)` çıkarımı (`accuracy.py` deseni) → `analytics/nominal.py` (DRY).
- **Idempotency (hibrit):** production/orders doğal PK + `DO UPDATE`; events `(source_file,
  row_ordinal)` + `DO NOTHING`.
- **Eşzamanlılık:** tek DuckDB bağlantısı bir kilitle serileştirilir (pano paralel istek atar;
  aksi halde segfault).
- **Determinizm:** sabitler config'te; golden fixture'lar simülatörden seed 42 (statik commit'li,
  test anında simülatör bağımlılığı yok).

## Bilinen sınırlamalar / takip işleri (planlamaya girdi)

- **G4.1 — dönem-doğru üretim atfı:** ✓ ÇÖZÜLDÜ (Dalga 3). `events.csv`'ye `carrier_id` eklendi;
  `fetch_production(frm,to)` askıyı kendi olaylarının en geç zaman damgasına göre pencereye bağlar →
  trend ve replay'de **P/Q pencere bazında doğru** değişir.
- **Utilization formülü:** ✓ ÇÖZÜLDÜ (H8, `feat/dalga-c-h8-h9`). `analytics/calendar.py`
  `calendar_minutes` gerçek takvimden (workday ∩ vardiya − mola − bakım; örtüşme bir kez) hesaplar;
  utilization = çalışılan / takvim-zamanı. A/P/Q/OEE değişmez (yalnız utilization). Mola/bakım çift
  sayılmaz, vardiya-dışı dışlanır.
- **Pano frontend:** **React 19 + Vite SPA** (GR). FastAPI build çıktısını (`app/frontend_dist/`,
  gitignore'lu; Docker stage-1 üretir) `/`'ta sunar; eski Jinja `/legacy`'de fallback. Dev'de
  `frontend/` Vite sunucusu backend'e (8000) proxy'ler. JSON sözleşmesi backend'le aynı.
- **G8 kalibrasyon kararı (doğal-eksen):** TL ağırlıkları dengesiz (DOWNTIME 50 pahalı; SPEED 20,
  REDO 3, FILL 2 ucuz) → ucuz kanallar TL'de #1 olamaz. Kapı (`test_scenarios_dominant_loss`) her
  senaryonun adlı kaybını **kendi ekseninde** (zaman→dakika, malzeme→parça) baskın doğrular.
  Daha gerçekçi senaryolar + okunabilir demo (pano ilgili grafiği gösterir).

## Sıradaki yol haritası

**Dalga 2 TAMAM** (G8 · GR · G7). **Dalga 3 TAMAM** (G12 · G4.1 · G10 · Perf-UI).
**Hazırlık Dalga A TAMAM** (H1 · H2 · H3):
- **H1 — Kirli-veri dayanıklılığı:** `tools/corrupt.py` (10 tür, seed'li); loader ham-CSV/encoding'de
  zarif-bozulma; EventRow negatif-duration validator; `tests/fixtures/dirty/`; `data_quality.coverage`
  `sufficient` sinyali; out-of-order/duplicate span+union testleri.
- **H2 — Konfigürasyonla ingest adaptörü:** `app/ingest/adapter.py` `apply_mapping` + `AdapterConfig`;
  `config/adapters/generic_plant.yaml` + `tests/fixtures/raw/`; `POST /ingest?adapter=<profil>`.
- **H3 — Belirsizlik/güven:** `app/analytics/confidence.py` `data_sufficiency` + `band` (baseline'da
  ground_truth'u KAPSAR); `cost.to_tl` → `tl_low/tl_high/confidence/low_confidence`; pano "düşük güven" rozeti.

**Hazırlık Dalga B TAMAM** (H4 · H5 · H6 · H7):
- **H4 — Çok-seed + hat varyasyonları:** `fixtures/multiseed/` N=10 + `test_multiseed_parity` (DAĞILIM
  parite: ortalama ±%1, geri kazanım medyanı ≥%85); simülatör `config/lines/` 2 varyasyon.
- **H5 — Duyarlılık analizi:** `simulator/tools/sensitivity.py` + `docs/sensitivity_report.md`
  (speed_loss en yüksek etki, fill_loss en düşük).
- **H6 — Demo cilası:** `ScenarioInfo` `narrative`/`highlight`; pano `ScenarioDropdown` anlatısı.
- **H7 — Hat-tanımı doğrulayıcı:** `app/config_validate.py` + `POST /line/validate` + `docs/line-definition-guide.md`.

**Hazırlık Dalga C TAMAM** (H8 · H9):
- **H8 — Utilization/takvim:** `app/analytics/calendar.py` `calendar_minutes` (workday ∩ vardiya −
  mola − bakım); utilization = çalışılan/takvim. A/P/Q/OEE değişmez.
- **H9 — Ops:** loglama (`logging_setup` + timing middleware), tutarlı 400 (`_params` + global handler),
  perf smoke (~12 hafta < 2s), `docs/deployment.md`. Yan düzeltme: `fetch_events` tarih filtresi CAST.

**Sırada:** **pilot kiti / saha denemesi**. Olası ileri işler: simülatör destekli what-if (GainEstimator arayüzü hazır), çok-hatlı destek.

### G7 replay — artık dönem-doğru (G4.1 sonrası)
Replay penceresi G4.1 ile **üretime de uygulanır** (carrier_id zaman atfı) → Availability + kayıp-zaman +
TL ile birlikte **P/Q de pencere-doğru büyür**. Final snapshot (to=None) statik `/oee` ile birebir kalır.
What-if köprüsü: replay motoru + senaryo parametresi = dijital-ikiz-lite zemini.

## CI

GitHub Actions (`.github/workflows/ci.yml`) her push/PR'da **iki paralel job**:
- **test** (Python 3.11): `ruff check` + `pytest -q`. Parite eşikleri (OEE ±%1, kayıpsız OEE ≥%95,
  gizli kanal ≥%85, firewall) `test_regression_contract.py`'de açık sabitlerle (`@pytest.mark.regression`).
- **frontend** (Node 20): `npm ci` + `npm run lint` + `npm run test` (vitest) + `npm run build`.

Yerelde backend kapısı: `make ci`.

## Çalıştırma

```
docker compose up --build          # http://localhost:8000  (React SPA, açılışta baseline yüklü)
                                   #   /legacy = eski Jinja pano
# backend testleri:  cd backend && pytest -q          (94 test)
# frontend dev:      cd frontend && npm run dev        (Vite, backend'e proxy)
# frontend testleri: cd frontend && npm run test       (vitest 2)
```

## Deploy (başkalarının erişmesi için)

- **Docker yerelde doğrulandı** (2026-06-18): Docker Desktop 29.5.3; `docker compose up --build`
  imajı kurup `:8000`'de servis ediyor (pano + Dalga 3 + cyan cilası; OEE 0.601). Gotcha: bu
  shell oturumunda `docker-credential-desktop` PATH'te değilse build patlar → bin dizinini PATH'e ekle.
- **Render Blueprint** (`render.yaml`): tek Docker web servisi (frankfurt, free, `/health`,
  `$PORT` desteği, açılışta baseline auto-ingest). Render → New → Blueprint → repo → Apply.
  `autoDeploy: true` → `main`'e push otomatik redeploy. Aynı imaj Railway/Fly'da da çalışır.
- **Erişim katmanı:** form-tabanlı, tema-uyumlu giriş ekranı (`app/auth.py`, imzalı çerez).
  `OEE_AUTH_PASS` env tanımlıysa pano giriş arkasına alınır (kullanıcı `OEE_AUTH_USER`, vars. `admin`);
  tanımsızsa kapalı (yerel/test açık). `/health` daima public. Render'da şifre Dashboard'dan girilir
  (`render.yaml`: `OEE_AUTH_PASS sync:false`, `OEE_AUTH_SECRET generateValue`). Test: `test_auth.py`.

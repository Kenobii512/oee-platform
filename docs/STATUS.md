# OEE Platform — Proje Durumu (planlama özeti)

**Güncelleme:** 2026-06-16 · **Repo:** `Kenobii512/oee-platform` (private) · **Test:** backend 83/83 + frontend vitest 2/2 yeşil
**Yığın:** Python 3.11 · FastAPI · DuckDB · Docker · **pano: React 19 + Vite (SPA)** (eski Jinja `/legacy`'de)

Bu doküman, bir sonraki planlama oturumu için "ne bitti, ne nasıl çalışıyor, sırada ne var"
özetidir. Ayrıntılı tasarım/plan: `docs/superpowers/specs` ve `docs/superpowers/plans`.

---

## Tamamlanan görevler (G1–G5 · Dalga 1: G6·G11·G9 · Dalga 2: G8·GR)

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

## API yüzeyi (mevcut)

```
GET  /health                          -> {"status":"ok"}
POST /ingest        {"path": "..."}    -> LoadReport (kabul/ret/atlanan + ilk N hata)
GET  /oee?from=&to=                    -> {availability, performance, quality, oee, utilization, planned_downtime_min}
GET  /loss-tree?from=&to=              -> {categories:[{category, axis, value, kind}]}  (6 kategori)
GET  /loss-tree/cost?from=&to=         -> {categories:[{category, axis, value, tl, kind}], total_tl}  (TL azalan)
GET  /recommendations?from=&to=        -> {recommendations:[{category, tl, estimated_gain_tl, title, action, assumption, ...}], total_estimated_gain_tl}
GET  /oee/trend?bucket=day|week        -> [{period, availability, performance, quality, oee}]
GET  /data-quality/summary             -> {downtime_entry_coverage, microstop_entry_coverage}
GET  /scenarios                        -> {scenarios:[{id, title, description, expected_top_loss, data_dir}]}  (6 demo)
POST /scenarios/{id}/activate          -> {activated, ingest}  (repo.reset() + o senaryoyu ingest)
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

- **G4.1 — dönem-doğru üretim atfı:** `events.csv`'de `carrier_id` yok → production zaman
  pencerelerine bölünemiyor. Bugün `from/to` yalnız events'e uygulanıyor; trend'de P/Q dönem-geneli
  sabit, yalnız Availability pencere bazında değişiyor. Pencere-doğru P/Q için ingest'te carrier'a
  dönem damgası gerekir.
- **Utilization formülü:** `calendar = span + planned_downtime_min` basit bir MVP; span içine düşen
  planlı bakım çift sayılabilir, vardiya-dışı/molalar hariç. Parite testi yok; G10/takvim modeliyle
  netleşecek.
- **Pano frontend:** **React 19 + Vite SPA** (GR). FastAPI build çıktısını (`app/frontend_dist/`,
  gitignore'lu; Docker stage-1 üretir) `/`'ta sunar; eski Jinja `/legacy`'de fallback. Dev'de
  `frontend/` Vite sunucusu backend'e (8000) proxy'ler. JSON sözleşmesi backend'le aynı.
- **G8 kalibrasyon kararı (doğal-eksen):** TL ağırlıkları dengesiz (DOWNTIME 50, SCRAP 8 pahalı;
  SPEED 20, REDO 3, FILL 2 ucuz) → ucuz kanallar TL'de #1 olamaz. Kapı (`test_scenarios_dominant_loss`)
  her senaryonun adlı kaybını **kendi ekseninde** (zaman→dakika, malzeme→parça) baskın doğrular.
  Daha gerçekçi senaryolar + okunabilir demo (pano ilgili grafiği gösterir).

## Sıradaki yol haritası

**Dalga 2 kalan:** **G7** (hızlandırılmış replay — SSE; React üstünde canlı). Bkz
`docs/superpowers/plans/2026-06-16-oee-wave2-g8-gr-g7.md`.
**Dalga 3:** G10 (tam veri-kalite paneli) → G4.1 (dönem-doğru üretim atfı) → Pilot kiti.

## CI

GitHub Actions (`.github/workflows/ci.yml`) her push/PR'da **iki paralel job**:
- **test** (Python 3.11): `ruff check` + `pytest -q`. Parite eşikleri (OEE ±%1, kayıpsız OEE ≥%95,
  gizli kanal ≥%85, firewall) `test_regression_contract.py`'de açık sabitlerle (`@pytest.mark.regression`).
- **frontend** (Node 20): `npm ci` + `npm run lint` + `npm run test` (vitest) + `npm run build`.

Yerelde backend kapısı: `make ci`.

## Çalıştırma

```
docker-compose up --build          # http://localhost:8000  (React SPA, açılışta baseline yüklü)
                                   #   /legacy = eski Jinja pano
# backend testleri:  cd backend && pytest -q          (83 test)
# frontend dev:      cd frontend && npm run dev        (Vite, backend'e proxy)
# frontend testleri: cd frontend && npm run test       (vitest)
```

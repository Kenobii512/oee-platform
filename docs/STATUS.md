# OEE Platform — Proje Durumu (planlama özeti)

**Güncelleme:** 2026-06-14 · **Repo:** `Kenobii512/oee-platform` (private) · **Test:** 49/49 yeşil
**Yığın:** Python 3.11 · FastAPI · DuckDB · Docker · (pano) Jinja2 + Chart.js

Bu doküman, bir sonraki planlama oturumu için "ne bitti, ne nasıl çalışıyor, sırada ne var"
özetidir. Ayrıntılı tasarım/plan: `docs/superpowers/specs` ve `docs/superpowers/plans`.

---

## Tamamlanan görevler (G1–G5)

| Görev | Teslim | Durum |
|------|--------|-------|
| **G1** | Repo iskeleti, veri sözleşmesi (pydantic), `Repository` arayüzü, `/health`, ADR + data-contract | ✓ |
| **G2** | CSV ingest (doğrulama + firewall + idempotency), DuckDB depo, `POST /ingest` | ✓ |
| **G3** | OEE motoru (A/P/Q/OEE) — yalnız public veriden; simülatör `metrics.py` ile **birebir** parite | ✓ |
| **G4** | Kayıp ağacı (6 kategori, gizli kanal çıkarımı), `GET /loss-tree` | ✓ |
| **G5** | Minimal pano (KPI, şelale, kayıp ağacı, trend, veri-kalite) + premium redesign | ✓ |

## API yüzeyi (mevcut)

```
GET  /health                          -> {"status":"ok"}
POST /ingest        {"path": "..."}    -> LoadReport (kabul/ret/atlanan + ilk N hata)
GET  /oee?from=&to=                    -> {availability, performance, quality, oee, utilization, planned_downtime_min}
GET  /loss-tree?from=&to=              -> {categories:[{category, axis, value, kind}]}  (6 kategori)
GET  /oee/trend?bucket=day|week        -> [{period, availability, performance, quality, oee}]
GET  /data-quality/summary             -> {downtime_entry_coverage, microstop_entry_coverage}
GET  /                                 -> pano (HTML)
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
- **Pano frontend:** sunucu-taraflı (Jinja2 + Chart.js CDN), build yok. Daha interaktif ekranlar
  (G7 replay) için React/Vite'a geçiş düşünülebilir.

## Sıradaki yol haritası (V2 — `OEE_V2_Yol_Haritasi.docx`)

- **G6** — Regresyon: doğruluk testlerini CI'da eşikli hale getir (görünür ±%1, gizli ≥%85, OEE parite).
- **G7** — Hızlandırılmış replay: panoyu canlıymış gibi besle (burada React'e geçiş gündeme gelebilir).
- **G8** — Senaryo kütüphanesi: farklı kayıp profillerini demo/karşılaştırma için yönet.
- **G9** — Kural tabanlı öneri: kayıp ağacından en büyük kaybı bulup öneri üret (panoya "Öneriler").
- **G10** — Tam veri-kalite / operatör atıf paneli (G5'teki tek gösterge bunun habercisi).
- **G11** — TL lensi: kategorileri ortak birime (TL) çevir → gerçek Pareto + parasal etki.

## Çalıştırma

```
docker-compose up --build          # http://localhost:8000  (uzak VM'de link ile aynı imaj)
# demo: SAMPLE_DATA_DIR=/app/tests/fixtures/baseline ile açılışta otomatik dolu pano
cd backend && pytest -v            # 49 test
```

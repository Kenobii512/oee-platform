# OEE Platform

Kaplama hattı için OEE/verimlilik platformu. Genel CSV'leri (events/production/orders)
DuckDB'ye yükler ve OEE'yi **yalnızca genel veriden** hesaplar; kaybı bulur, TL'ye çevirir
ve önceliklendirilmiş öneriler üretir. Pano **React 19 + Vite SPA**; canlı (hızlandırılmış)
replay dahil.

> **Proje durumu / yol haritası:** [`docs/STATUS.md`](docs/STATUS.md) — tamamlanan görevler
> (G1–G5 · Dalga 1 G6·G11·G9 · Dalga 2 G8·GR·G7 · Dalga 3 G12·G4.1·G10·Perf-UI), API yüzeyi,
> mimari kararlar, bilinen sınırlamalar. **Veri sözleşmesi:** [`docs/data-contract.md`](docs/data-contract.md).

## Çalıştırma (Docker)

```bash
docker compose up --build      # http://localhost:8000  (açılışta baseline senaryo yüklü)
```
Aynı imaj laptopta `localhost:8000` ve uzak sunucuda public URL ile çalışır. Açılışta
`SAMPLE_DATA_DIR` (compose'da ayarlı) baseline senaryoyu otomatik ingest eder → pano dolu gelir.

## Geliştirme

```bash
cd backend && pip install -r requirements.txt && pytest -q     # 92 test
cd frontend && npm install && npm run dev                      # Vite (backend'e :8000 proxy)
cd frontend && npm run lint && npm run test && npm run build   # vitest + üretim build
```

## İlkeler

- **Şema kutsaldır;** platform verinin simülatörden mi sahadan mı geldiğini bilmez.
- **Firewall:** `ground_truth.csv` ASLA yüklenmez; gerçek yalnız doğrulama testlerinde.
- **Tek doğruluk kaynağı:** OEE/kayıp mantığı platformda; simülatör `metrics.py` yalnız parite referansı.
- **No-scrap modeli (G12):** spec-dışı parça hurdaya gitmez, sıyrılıp iyi olana dek tekrar kaplanır.

## API yüzeyi

```
GET  /health                          -> {"status":"ok"}
POST /ingest        {"path": "..."}    -> LoadReport
GET  /oee?from=&to=                    -> {availability, performance, quality(=ilk-geçiş), oee,
                                          utilization, planned_downtime_min, final_yield}
GET  /loss-tree?from=&to=             -> {categories:[{category, axis, value, kind}]}  (5 kategori)
GET  /loss-tree/cost?from=&to=        -> {categories:[...,tl], total_tl}  (TL azalan)
GET  /recommendations?from=&to=       -> {recommendations:[{category, tl, estimated_gain_tl,
                                          estimated_gain_tl_low/high, title, action, assumption}], ...}
GET  /oee/trend?bucket=day|week       -> [{period, availability, performance, quality, final_yield, oee}]
GET  /data-quality/summary            -> {microstop_entry_coverage}   (G10: tek manuel girdi)
GET  /scenarios                       -> {scenarios:[...]}  (6 demo)
POST /scenarios/{id}/activate         -> repo.reset() + o senaryoyu ingest
GET  /replay/stream?scenario=&speed=&steps=  -> SSE: büyüyen 'şimdiye kadar' snapshot'ları
GET  /                                -> React SPA   ·   GET /legacy -> Jinja fallback
```

## Kayıp ağacı & kalite (Dalga 3)

`GET /loss-tree` **5 kategori** döndürür: DOWNTIME/MICROSTOP (dakika, görünür),
QUALITY_REDO (parça, görünür), FILL_LOSS (parça, çıkarım), SPEED_LOSS (dakika, çıkarım).
Görünür kanallar genel veriden doğrudan; gizli kanallar (doluluk/hız) yalnız çıkarımla
kestirilir. Çıkarım fonksiyonu `ground_truth` almaz (firewall).

OEE'nin Q'su **ilk-geçiş kalite** = `(loaded − redo)/loaded` (redo'yu cezalandırır); ayrıca
**`final_yield`** = `good/loaded` (≈%100, no-scrap'i görünür kılar). G4.1 ile `events.csv`'ye
`carrier_id` eklendiğinden trend/replay'de Performance ve Quality **pencere-doğru** değişir.

## Deploy (başkalarının erişmesi için)

Çok-aşamalı `backend/Dockerfile` (Vite build + Python backend) ve [`render.yaml`](render.yaml)
hazırdır. Render: **New → Blueprint → bu repo → Apply** ile tek tıkla deploy (free, frankfurt,
`$PORT` desteği, `/health` kontrolü). Aynı imaj Railway/Fly/herhangi bir konteyner host'unda
çalışır. Not: uygulamada kimlik doğrulama yok — public URL'i olan herkes panoyu görür.

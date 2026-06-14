# OEE Platform

Kaplama hattı için OEE/verimlilik platformu. Genel CSV'leri (events/production/orders)
DuckDB'ye yükler ve OEE'yi yalnızca genel veriden hesaplar.

## Çalıştırma

    docker-compose up --build
    # GET http://localhost:8000/health -> {"status":"ok"}

## Test

    cd backend
    pip install -r requirements.txt
    pytest -v

## İlkeler

- Şema kutsaldır; platform verinin kaynağını bilmez.
- `ground_truth.csv` ASLA yüklenmez (firewall).
- OEE mantığı tek serviste (`app/analytics/oee.py`).

## OEE

    POST /ingest   {"path": "/abs/path/to/csv_dir"}   -> LoadReport
    GET  /oee?from=...&to=...                          -> {availability, performance, quality, oee, utilization, planned_downtime_min}
    GET  /loss-tree?from=...&to=...                    -> {categories: [{category, axis, value, kind}, ...]}

OEE yalnız genel veriden (events/production + hat tanımı) hesaplanır; tanımlar
simülatör `metrics.py` ile birebir. `ground_truth.csv` asla kullanılmaz.

## Kayıp ağacı (loss tree)

`GET /loss-tree` 6 kategori döndürür: DOWNTIME/MICROSTOP (dakika, görünür),
QUALITY_REDO/QUALITY_SCRAP (parça, görünür), FILL_LOSS (parça, çıkarım),
SPEED_LOSS (dakika, çıkarım). Görünür kanallar genel veriden doğrudan; gizli kanallar
(doluluk/hız) yalnız çıkarımla kestirilir (`app/analytics/loss_tree.py`). Çıkarım
fonksiyonu `ground_truth` almaz (firewall). Kategoriler farklı eksende olduğundan
ortak birime (TL) çevirme ve Pareto sıralaması G11'dedir.

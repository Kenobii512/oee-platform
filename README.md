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

OEE yalnız genel veriden (events/production + hat tanımı) hesaplanır; tanımlar
simülatör `metrics.py` ile birebir. `ground_truth.csv` asla kullanılmaz.

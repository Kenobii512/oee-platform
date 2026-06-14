# ADR 0001 — Mimari Kararı

## Bağlam
Kaplama hattı için OEE platformu. Veri sahadan veya simülatörden gelir; platform farkı
bilmemeli.

## Karar
- **Yığın:** Python 3.11 + FastAPI (backend) + DuckDB (depo) + Docker (tek konteyner).
- **Katmanlar:** `api → analytics/ingest → store(Repository) → duckdb`, tek yönlü bağımlılık.
  İş mantığı somut DuckDB'yi tanımaz; `Repository` Protocol'üne bağlıdır.
- **Dağıtım:** Tek konteyner (laptop + VM). Veri DuckDB dosyasında.
- **DuckDB→Postgres:** Gömülü DuckDB ile başlanır (sıfır kurulum, hızlı analitik). Ölçek/
  çok-kullanıcı gerekince `duckdb_repo.py` Postgres uygulamasıyla değiştirilir; arayüz sabit.
- **OEE tek doğruluk kaynağı:** Hesap `analytics/oee.py`'de toplanır; simülatör `metrics.py`
  yalnız referans/regresyon.

## Kapsam dışı
Kubernetes, çok-kiracılık, what-if motoru, gerçek-zamanlı akış. Sonraki sürümlerde.

## Sonuç
Hızlı, tek-konteyner, test edilebilir iskelet; veri katmanı geleceğe karşı yalıtılmış.

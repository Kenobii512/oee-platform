.PHONY: test lint ci doctor clean frontend-sync

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check .

ci: lint test

# Pilot Doctor: Faz 0-1 GO/NO-GO kapisi (vars. baseline = kendi kendini dogrulama).
# DATA repo kokune gore verilir; abspath cd backend oncesi mutlaklastirir.
DATA ?= backend/tests/fixtures/baseline
doctor:
	cd backend && python -m tools.pilot_doctor "$(abspath $(DATA))"

# Yereldeki basibos DuckDB dosyalarini temizle (eski .duckdb -> BinderException tuzagi).
clean:
	cd backend && rm -f *.duckdb *.duckdb.wal

# React build'ini backend'in sundugu dizine kopyala (native calistirma icin;
# Docker kendi stage'inde uretir). QC bulgusu: bayat dist 9 gunluk UI sunuyordu.
frontend-sync:
	cd frontend && npm run build
	rm -rf backend/app/frontend_dist
	cp -r frontend/dist backend/app/frontend_dist

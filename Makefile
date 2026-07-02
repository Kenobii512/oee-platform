.PHONY: test lint ci doctor clean

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

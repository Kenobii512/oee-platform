.PHONY: test lint ci doctor

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check .

ci: lint test

# Pilot Doctor: Faz 0-1 GO/NO-GO kapisi (vars. baseline = kendi kendini dogrulama).
DATA ?= tests/fixtures/baseline
doctor:
	cd backend && python -m tools.pilot_doctor $(DATA)

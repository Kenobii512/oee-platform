.PHONY: test lint ci

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check .

ci: lint test

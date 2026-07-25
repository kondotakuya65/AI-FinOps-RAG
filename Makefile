.PHONY: backend-install backend-run test health fixtures ingest eval

backend-install:
	cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt || .venv/bin/pip install -r requirements.txt

backend-run:
	cd backend && uvicorn app.main:app --reload --port 8000

test:
	cd backend && pytest

health:
	curl -s http://localhost:8000/api/health

fixtures:
	cd backend && .venv/Scripts/python ../scripts/generate_fixtures.py || .venv/bin/python ../scripts/generate_fixtures.py

ingest:
	cd backend && .venv/Scripts/python -m app.ingest.cli || .venv/bin/python -m app.ingest.cli

eval:
	cd backend && .venv/Scripts/python -m app.eval.cli || .venv/bin/python -m app.eval.cli

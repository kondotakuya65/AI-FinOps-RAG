.PHONY: backend-install backend-run test health

backend-install:
	cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt || .venv/bin/pip install -r requirements.txt

backend-run:
	cd backend && uvicorn app.main:app --reload --port 8000

test:
	cd backend && pytest

health:
	curl -s http://localhost:8000/api/health

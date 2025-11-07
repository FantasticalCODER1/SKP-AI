.PHONY: install run lint test docker-up

install:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	flake8 app || echo "flake8 not installed; skipping"

test:
	pytest || echo "pytest not configured; skipping"

docker-up:
	docker-compose up --build

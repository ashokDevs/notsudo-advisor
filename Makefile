.PHONY: up db-shell serve lint

up:
	docker-compose up -d

db-shell:
	docker-compose exec postgres psql -U user -d notsudo

serve:
	uvicorn api.app:app --reload --port 8080

lint:
	ruff check . && mypy --strict .

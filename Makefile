.PHONY: up db-shell serve serve-public lint test scan demo eval docker-build docker-run

up:
	docker-compose up -d

db-shell:
	docker-compose exec postgres psql -U user -d notsudo

serve:
	uvicorn api.app:app --reload --host 127.0.0.1 --port 8080

# Bind all interfaces — use with ngrok or LAN access
serve-public:
	uvicorn api.app:app --host 0.0.0.0 --port 8080

lint:
	ruff check . && mypy --strict .

test:
	pytest tests/unit tests/test_smoke.py -q

scan:
	python -m cli.main scan demo_app

demo: scan

eval:
	python -m eval.run

docker-build:
	docker build -t notsudo .

docker-run:
	docker run --rm -p 8080:8080 --env-file .env -e APP_BASE_URL=http://localhost:8080 notsudo

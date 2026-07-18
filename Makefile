.PHONY: up db-shell

up:
	docker-compose up -d

db-shell:
	docker-compose exec postgres psql -U user -d notsudo

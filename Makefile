.PHONY: up down restart build logs clean nuke

# ── Default ────────────────────────────────────────────────────────────────
up:
	docker compose up --build -d

# ── Stop containers, keep all data (named volumes + bind mounts) ───────────
down:
	docker compose down

# ── Full restart: down then up ─────────────────────────────────────────────
restart: down up

# ── Rebuild images without starting ───────────────────────────────────────
build:
	docker compose build

# ── Follow logs for all services (Ctrl+C to exit) ─────────────────────────
logs:
	docker compose logs -f

# ── Follow logs for a specific service: make logs-bff ─────────────────────
logs-%:
	docker compose logs -f $*

# ── Remove containers + named volumes (redis, rabbitmq, grafana, certs) ───
# bind-mount data (postgres, mongodb, prometheus) in ./data/ is NOT touched.
clean:
	docker compose down -v

# ── Full wipe: named volumes + bind-mount data directories ────────────────
# WARNING: destroys ALL local data. Use only to start from a clean slate.
nuke: clean
	rm -rf data/postgres data/mongodb data/prometheus

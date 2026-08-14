#!/bin/sh
# Runs once per container start, before the API comes up: migrate, load the
# structured data, ingest the source PDFs. Every step here is idempotent
# (see the scripts themselves), so this is safe on a fresh volume AND on a
# plain restart of an already-seeded stack - a clean `docker compose up` on
# a brand new clone needs zero manual steps beyond creating .env.
set -e

echo "==> Running migrations"
uv run alembic upgrade head

echo "==> Loading structured data (students, courses, enrollments, ...)"
uv run python -m app.scripts.load_data

echo "==> Ingesting source documents (Handbook, Catalogue)"
uv run python -m app.scripts.ingest_documents

echo "==> Starting API"
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

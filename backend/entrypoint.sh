#!/bin/sh
# entrypoint.sh
#
# Sub-commands
# ────────────
#   migrate  Run Alembic migrations to head, then exit.
#            Used by the Kubernetes / Helm pre-install and pre-upgrade Job.
#
#   serve    Start Uvicorn application server (default).
#            Application pods should use this command (or omit CMD entirely).
#
#   <other>  Pass-through: exec the arguments directly.
#            Useful for one-off debugging (e.g. bash, alembic history).
#
# Environment variables consumed here
# ─────────────────────────────────────
#   DATABASE_URL      Required for both migrate and serve.
#   WEB_CONCURRENCY   Number of Uvicorn worker processes (default: 1).
#                     Kubernetes horizontal scaling is preferred; increase only
#                     if per-pod profiling justifies multiple workers.

set -e

case "$1" in
  migrate)
    echo "Running database migrations..."
    exec alembic upgrade head
    ;;
  serve|"")
    echo "Starting application (workers=${WEB_CONCURRENCY:-1})..."
    exec uvicorn app.main:app \
      --host 0.0.0.0 \
      --port 8000 \
      --workers "${WEB_CONCURRENCY:-1}"
    ;;
  *)
    exec "$@"
    ;;
esac

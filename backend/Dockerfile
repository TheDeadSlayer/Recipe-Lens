# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — python-deps
#   Installs only runtime dependencies (requirements.txt).
#   Test and dev packages are never installed here.
#   Using a separate stage means the final image only contains what the
#   running application needs, with no pip cache and no build tooling.
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS python-deps

WORKDIR /deps

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — runtime
#   Starts from a clean python:3.12-slim base.
#   Copies installed site-packages from the deps stage — no pip re-run.
#   Copies application source (tests, scripts, .env excluded by .dockerignore).
#   Runs as a non-root user (uid 1001).
#
# Sub-commands (see entrypoint.sh):
#   migrate  — run Alembic migrations, then exit (used by Helm Job)
#   serve    — start Uvicorn (default CMD, used by application pods)
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Create a non-root user with a fixed UID so pod security policies can reference it.
RUN useradd --create-home --uid 1001 --shell /bin/bash appuser

WORKDIR /app

# Copy installed packages from the deps stage.
# Copying both site-packages and bin/ picks up console-script entry points
# (uvicorn, alembic) as well as all library code.
COPY --from=python-deps /usr/local/lib/python3.12/site-packages \
                        /usr/local/lib/python3.12/site-packages
COPY --from=python-deps /usr/local/bin \
                        /usr/local/bin

# Copy application source.
# .dockerignore excludes: tests/, scripts/, .env, .env.*, __pycache__, *.md,
# .pytest_cache, .git, dist/, *.egg-info, IDE files.
COPY --chown=appuser:appuser . .

# Wire up the entrypoint.
COPY --chown=appuser:appuser entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

EXPOSE 8000

# WEB_CONCURRENCY controls the number of Uvicorn worker processes.
# Default is 1 — let Kubernetes replicas/HPA provide horizontal scaling.
# Increase deliberately per-environment if per-pod profiling justifies it.
ENV WEB_CONCURRENCY=1

ENTRYPOINT ["/entrypoint.sh"]
# Default: start the application server.
# Override with CMD ["migrate"] in the Helm migration Job.
CMD ["serve"]

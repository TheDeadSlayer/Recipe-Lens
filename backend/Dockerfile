FROM python:3.12-slim AS base

WORKDIR /app

# ── Dependency layer ──────────────────────────────────────────────────────────
# psycopg2-binary bundles libpq — no system packages needed
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Final image ───────────────────────────────────────────────────────────────
FROM deps AS final

# Run as non-root
RUN useradd --create-home --shell /bin/bash appuser

COPY --chown=appuser:appuser entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

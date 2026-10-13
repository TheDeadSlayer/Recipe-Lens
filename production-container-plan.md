# Production Container Hardening Plan

## Overview

Harden both application images for Kubernetes/AKS deployment.
No application features change. No Azure infrastructure, Terraform, Helm, or GitHub Actions are created here.

The goal is:
- Backend and frontend images that are safe, minimal, and AKS-ready
- A migration sub-command so the same backend image can be used as a Helm pre-install Job
- A fully non-root frontend Nginx container on port 8080 with no backend proxy responsibility
- Clean .dockerignore files on both services
- Verified with local production-image smoke tests and the existing test suites

---

## Architecture decisions (approved)

### Backend migration strategy
- `entrypoint.sh` accepts a `migrate` sub-command → runs `alembic upgrade head`, then exits
- `entrypoint.sh` accepts a `serve` sub-command (default) → starts Uvicorn, no migration
- AKS will use a Helm `pre-install`/`pre-upgrade` Job that runs the same image with `args: ["migrate"]`
- Application pods use `args: ["serve"]` (or omit args to use the default CMD)

### Frontend /api routing
- Frontend JS uses relative `/api/v1/...` URLs only (VITE_API_BASE_URL="" at production build time)
- Nginx serves only static assets; it does NOT proxy /api/ to the backend
- In AKS: the Kubernetes Ingress routes `/api/*` → backend Service, `/*` → frontend Service
- In local production testing: a `docker-compose.prod.yml` companion puts Nginx in front of both services and handles the split routing internally, OR the user hits the backend directly on :8000 for the API
- CORS: in production the Ingress makes both services same-origin so CORS headers are not needed for browser requests
- Local dev (Vite) continues using `VITE_API_BASE_URL=http://localhost:8000` pointing directly at the backend

### Nginx non-root / port 8080
- Use `nginxinc/nginx-unprivileged:1.27-alpine` base image which is pre-configured to run as non-root on port 8080
- No capability grants, no root escalation
- Kubernetes Service maps external port 80 → container port 8080 via targetPort

---

## Sub-Tasks

### Sub-Task 1 — Split backend requirements into runtime and dev

**Intent**
Move test-only packages (pytest, pytest-cov, httpx) out of requirements.txt into a new requirements-dev.txt so the production image installs only what the running application needs.

**Expected Outcomes**
- `backend/requirements.txt` contains only packages needed to run the application
- `backend/requirements-dev.txt` contains test/dev packages and includes `-r requirements.txt` so a single install covers everything for local dev/CI
- The Dockerfile uses `requirements.txt` only
- All existing tests still pass (CI uses requirements-dev.txt)

**Todo List**
- [ ] Create `backend/requirements-dev.txt` with pytest, pytest-cov, httpx and `-r requirements.txt`
- [ ] Remove pytest, pytest-cov, httpx from `backend/requirements.txt`
- [ ] Verify `docker compose exec backend python -m pytest tests/` still works (it uses the mounted source, not the image)

**Relevant Context**
- `backend/requirements.txt` — current file mixing runtime and test deps
- `backend/tests/conftest.py` — runs migrations via subprocess; needs alembic in requirements.txt (already there, runtime dep)

**Status** `[ ] pending`

---

### Sub-Task 2 — Rewrite backend entrypoint and Dockerfile

**Intent**
Replace the unconditional `alembic upgrade head` on startup with a branching entrypoint that separates `migrate` from `serve`. Restructure the Dockerfile to use a clean two-stage build (deps → runtime) that copies only the installed site-packages rather than re-running pip in the final stage.

**Expected Outcomes**
- `entrypoint.sh` handles `migrate`, `serve`, and pass-through (`exec "$@"`)
- `CMD ["serve"]` is the default; a Helm Job will override to `["migrate"]`
- No `alembic upgrade head` runs at application pod startup
- Production image has no test packages
- `WEB_CONCURRENCY` env var controls worker count, defaults to 1
- Image still builds and starts correctly

**Todo List**
- [ ] Rewrite `backend/entrypoint.sh` with migrate/serve/passthrough branching
- [ ] Rewrite `backend/Dockerfile` as two-stage build: `python-deps` → `runtime`
  - Stage 1 (`python-deps`): pip install requirements.txt into /deps/
  - Stage 2 (`runtime`): copy site-packages from stage 1, copy app source, set non-root user uid 1001, expose 8000
- [ ] Add `ENV WEB_CONCURRENCY=1` and wire it into the uvicorn launch command
- [ ] Verify `docker build -t recipelens-backend:test backend/` succeeds
- [ ] Verify `docker run --rm recipelens-backend:test migrate` exits 0 (with a reachable DB) or fails with a clear DB error (not an application error)

**Relevant Context**
- `backend/entrypoint.sh` — current unconditional migration runner
- `backend/Dockerfile` — current single-stage-after-deps build
- `backend/app/main.py` — `/health` and `/ready` endpoints already exist; no changes needed
- `backend/alembic/env.py` — reads DATABASE_URL; the migrate sub-command needs this env var set

**Status** `[ ] pending`

---

### Sub-Task 3 — Harden backend .dockerignore

**Intent**
Ensure the backend build context contains no secrets, test files, dev scripts, or plan documents.

**Expected Outcomes**
- `backend/.dockerignore` excludes: scripts/, *.md, .git, any remaining test artefacts
- `backend/.env` and `backend/.env.*` remain excluded (already are)
- `backend/tests/` remains excluded (already is)
- `backend/entrypoint.sh` and application source are NOT excluded (must be included)

**Todo List**
- [ ] Add `scripts/` to `backend/.dockerignore`
- [ ] Add `*.md` to `backend/.dockerignore`
- [ ] Add `.git` to `backend/.dockerignore` (defence in depth even though build context is backend/)

**Relevant Context**
- `backend/.dockerignore` — current file

**Status** `[ ] pending`

---

### Sub-Task 4 — Rewrite frontend Dockerfile and nginx.conf for non-root port 8080

**Intent**
Replace the root-running nginx:alpine with the nginxinc/nginx-unprivileged:1.27-alpine image, which listens on port 8080 and runs as uid 101 out of the box. Remove all /api/ proxy_pass configuration — Nginx only serves static files. The Kubernetes Ingress will handle /api/ routing later.

**Expected Outcomes**
- Frontend image builds from `nginxinc/nginx-unprivileged:1.27-alpine`
- Container listens on 8080 as non-root (uid 101)
- SPA routing works: `try_files $uri $uri/ /index.html`
- Static asset cache headers preserved
- Security headers preserved
- No proxy_pass, no BACKEND_HOST, no envsubst
- `EXPOSE 8080` in Dockerfile
- No Node, no source files, no dev dependencies in the runtime image

**Todo List**
- [ ] Update `frontend/nginx.conf` — remove location /api/ block entirely; change listen to 8080
- [ ] Update `frontend/Dockerfile` — change runtime base to `nginxinc/nginx-unprivileged:1.27-alpine`; change EXPOSE to 8080; remove any envsubst references
- [ ] Verify `docker build -t recipelens-frontend:test frontend/` succeeds
- [ ] Verify container starts and `curl http://localhost:8080/` returns the React app HTML

**Relevant Context**
- `frontend/Dockerfile` — current production Dockerfile
- `frontend/nginx.conf` — current config with proxy_pass to backend
- The unprivileged Nginx image uses /etc/nginx/nginx.conf that already drops privileges and uses port 8080; the custom site config goes to /etc/nginx/conf.d/default.conf as before

**Status** `[ ] pending`

---

### Sub-Task 5 — Create frontend .dockerignore

**Intent**
The frontend build context currently has no .dockerignore. The Node builder stage would copy node_modules, dist, .env.example, test configs, and IDE files into the layer, wasting cache and potentially leaking local state.

**Expected Outcomes**
- `frontend/.dockerignore` exists and excludes at minimum:
  - node_modules/
  - dist/
  - .env (if any)
  - .env.local, .env.*.local
  - coverage/
  - .vscode/, .idea/
  - *.md (plan files etc.)
  - .DS_Store, Thumbs.db
- `frontend/.env.example` is NOT excluded (it is documentation, not secrets)
- Source files and config files needed for `npm run build` are included

**Todo List**
- [ ] Create `frontend/.dockerignore`

**Relevant Context**
- `frontend/` directory listing — node_modules/ and dist/ exist and must be excluded

**Status** `[x] done`

---

### Sub-Task 6 — Add docker-compose.prod.yml for local production validation

**Intent**
Provide a compose file that builds and runs the production images locally so the smoke test can be executed without the Vite dev server. The backend serves on 8000, the frontend (Nginx) serves on 8080. Since Nginx no longer proxies /api/, the smoke test for "API works through the frontend container" is instead verified by hitting the backend directly on :8000. The frontend smoke test verifies the SPA loads and React Router works.

The docker-compose.prod.yml also documents the environment variables production containers actually need (DATABASE_URL, LLM_PROVIDER, etc.) without containing real secrets.

**Expected Outcomes**
- `docker-compose.prod.yml` at the repo root
- `docker compose -f docker-compose.prod.yml up --build` starts postgres, backend (production image), and frontend (production Nginx image)
- `curl http://localhost:8000/health` → 200
- `curl http://localhost:8000/ready` → 200
- `curl http://localhost:8080/` → 200 HTML (React app)
- `curl http://localhost:8080/recipes` → 200 HTML (SPA routing via try_files)
- `curl http://localhost:8000/api/v1/recipes` → 200 JSON (backend API directly)
- Backend uses `CMD serve` (no migration at startup)
- A separate `docker compose -f docker-compose.prod.yml run --rm migrate` service can run the migration job

**Todo List**
- [ ] Create `docker-compose.prod.yml` with services: postgres, backend, frontend, and a `migrate` service (profile or separate service)
- [ ] Add a `migrate` service that overrides command to `migrate` and depends on postgres

**Relevant Context**
- `docker-compose.yml` — existing dev compose for reference
- `.env.example` — documents required env vars

**Status** `[x] done`

---

### Sub-Task 7 — Smoke test and full test suite validation

**Intent**
Prove both production images work end-to-end locally using the production compose file. Run the backend test suite against the running stack.

**Expected Outcomes**
- `docker compose -f docker-compose.prod.yml build` completes without error
- Migration job runs to completion
- Backend health/ready probes pass
- Frontend SPA loads from the Nginx container on :8080
- Backend API reachable on :8000
- All 181 backend tests pass
- All 37 frontend tests pass
- `npm run build` is clean (already verified but confirm after nginx.conf change)

**Todo List**
- [ ] Build both production images
- [ ] Run `docker compose -f docker-compose.prod.yml run --rm migrate`
- [ ] Start services and curl the health/ready/SPA/API endpoints
- [ ] Run `docker compose exec backend python -m pytest tests/ -q` against the running stack
- [ ] Run `npm test` in frontend/

**Relevant Context**
- Test invocations established in previous sessions
- Backend tests require TEST_DATABASE_URL pointing to the test database

**Status** `[x] done`

---

## Files changed summary

| File | Action |
|------|--------|
| `backend/requirements.txt` | Remove test deps |
| `backend/requirements-dev.txt` | New — test/dev deps |
| `backend/entrypoint.sh` | Rewrite — migrate/serve branching |
| `backend/Dockerfile` | Rewrite — two-stage, no test deps, WEB_CONCURRENCY |
| `backend/.dockerignore` | Extend — add scripts/, *.md, .git |
| `frontend/Dockerfile` | Edit — unprivileged nginx, EXPOSE 8080, no envsubst |
| `frontend/nginx.conf` | Edit — port 8080, remove /api/ proxy block |
| `frontend/.dockerignore` | New — exclude node_modules, dist, .env*, IDE files |
| `docker-compose.prod.yml` | New — local production validation compose |

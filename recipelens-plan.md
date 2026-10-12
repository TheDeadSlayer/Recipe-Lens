# RecipeLens — Architecture & Build Plan

## Overview

RecipeLens is a production-style demonstration project built to showcase software delivery,
DevOps, cloud infrastructure, IaC, containers, Kubernetes, and CI/CD.

The application accepts a cooking video URL, fetches its transcript, extracts a structured
recipe via an LLM, and persists the result to PostgreSQL. The application is intentionally
simple. The delivery and infrastructure layers are the primary demonstration surface.

**Repository:** git@github.com:TheDeadSlayer/recipe-lens.git
**Stack:** React + TypeScript · FastAPI · PostgreSQL · Docker · Azure · Terraform · AKS · Helm · GitHub Actions

---

## Architecture Decisions & Rationale

| Decision | Choice | Rationale |
|---|---|---|
| Job queue | FastAPI BackgroundTasks + PostgreSQL jobs table | Sufficient at demo scale. Intentional simplification — a production system would use Redis/Celery or a cloud messaging service. |
| LLM integration | `RecipeExtractor` interface; mock initially | Plugs in OpenAI/Azure OpenAI via env var with no code changes. |
| Transcript acquisition | `TranscriptProvider` interface; mock initially | Plugs in youtube-transcript-api later. Whisper is a future extension only. |
| Image tagging | Git commit SHA | Build once, promote the same artifact. Never use `latest` in CI/CD. |
| Terraform state | Azure Blob Storage remote backend | Shared, consistent state across local dev and CI. |
| Secrets | Azure Key Vault (CSI driver) | Production hardening — does not block initial deployment. |
| Observability | Azure Monitor + Application Insights | No extra cluster components; OTel tracing added in production-hardening stage. |
| Ansible | Not included | No legitimate config-management use case yet. Added later if one emerges. |

---

## Repository Structure

```
recipe-lens/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── types/
│   │   └── main.tsx
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── routes/
│   │   │       │   ├── jobs.py
│   │   │       │   └── recipes.py
│   │   │       └── router.py
│   │   ├── models/
│   │   │   ├── job.py
│   │   │   └── recipe.py
│   │   ├── schemas/
│   │   │   ├── job.py
│   │   │   └── recipe.py
│   │   ├── services/
│   │   │   ├── transcript/
│   │   │   │   ├── base.py          # TranscriptProvider ABC
│   │   │   │   ├── mock.py          # MockTranscriptProvider
│   │   │   │   └── youtube.py       # YouTubeTranscriptProvider (wired in later)
│   │   │   ├── llm/
│   │   │   │   ├── base.py          # RecipeExtractor ABC
│   │   │   │   ├── mock.py          # MockRecipeExtractor
│   │   │   │   └── openai.py        # OpenAIRecipeExtractor (wired in later)
│   │   │   └── recipe_pipeline.py   # Orchestrates transcript + LLM + DB write
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   │   ├── test_jobs.py
│   │   ├── test_recipes.py
│   │   ├── test_transcript_mock.py
│   │   └── test_llm_mock.py
│   ├── Dockerfile
│   └── requirements.txt
├── infra/
│   └── terraform/
│       ├── environments/
│       │   ├── dev/
│       │   │   ├── main.tf
│       │   │   ├── variables.tf
│       │   │   ├── outputs.tf
│       │   │   └── terraform.tfvars
│       │   └── prod/
│       │       ├── main.tf
│       │       ├── variables.tf
│       │       ├── outputs.tf
│       │       └── terraform.tfvars
│       └── modules/
│           ├── networking/        # VNet, subnets, NSGs
│           ├── aks/               # AKS cluster, node pool, managed identity
│           ├── acr/               # Azure Container Registry
│           ├── postgres/          # PostgreSQL Flexible Server
│           ├── keyvault/          # Key Vault, access policies
│           └── monitoring/        # Log Analytics, Application Insights, alerts
├── helm/
│   └── recipe-lens/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values-dev.yaml
│       ├── values-prod.yaml
│       └── templates/
│           ├── deployment-frontend.yaml
│           ├── deployment-backend.yaml
│           ├── service-frontend.yaml
│           ├── service-backend.yaml
│           ├── ingress.yaml
│           ├── configmap.yaml
│           ├── hpa.yaml
│           └── secretproviderclass.yaml
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Lint, test, build, push on every push/PR
│       └── cd.yml                 # Helm deploy on merge to main
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Service Abstractions

### TranscriptProvider

```
app/services/transcript/base.py    TranscriptProvider (ABC)
                                     fetch(url: str) -> str
app/services/transcript/mock.py    MockTranscriptProvider
                                     returns a realistic hardcoded transcript string
app/services/transcript/youtube.py YouTubeTranscriptProvider
                                     uses youtube-transcript-api (wired in later)
```

Active provider selected by `TRANSCRIPT_PROVIDER` env var:
- `mock` → `MockTranscriptProvider` (default; no external dependency)
- `youtube` → `YouTubeTranscriptProvider`

The mock returns a realistic multi-sentence transcript so the downstream mock
`RecipeExtractor` has plausible input to process.

### RecipeExtractor

```
app/services/llm/base.py           RecipeExtractor (ABC)
                                     extract(transcript: str) -> RecipeSchema
app/services/llm/mock.py           MockRecipeExtractor
                                     returns a valid hardcoded RecipeSchema fixture
app/services/llm/openai.py         OpenAIRecipeExtractor
                                     calls OpenAI / Azure OpenAI (wired in later)
```

Active provider selected by `LLM_PROVIDER` env var:
- `mock` → `MockRecipeExtractor` (default; no API key required)
- `openai` → `OpenAIRecipeExtractor`

No provider name, key, or model is hardcoded anywhere. All credentials come from
environment variables (`OPENAI_API_KEY`, `OPENAI_MODEL`).

---

## Data Model

### jobs

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| url | TEXT | Submitted video URL |
| status | TEXT | pending / processing / completed / failed |
| error | TEXT | Populated on failure, nullable |
| recipe_id | UUID | FK → recipes.id, nullable until completed |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### recipes

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| job_id | UUID | FK → jobs.id |
| title | TEXT | |
| ingredients | JSONB | List of ingredient name strings |
| quantities | JSONB | Parallel list of quantity strings |
| equipment | JSONB | List of equipment item strings |
| steps | JSONB | Ordered preparation step strings |
| calories | INTEGER | |
| protein_g | FLOAT | |
| carbs_g | FLOAT | |
| fat_g | FLOAT | |
| source_url | TEXT | Original video URL |
| created_at | TIMESTAMPTZ | |

---

## API Surface

All application routes are prefixed `/api/v1/`.

| Method | Path | Description |
|---|---|---|
| POST | /api/v1/jobs | Submit a video URL; returns job_id and status: pending |
| GET | /api/v1/jobs/{id} | Poll job status; returns recipe_id when completed |
| GET | /api/v1/recipes | List all recipes (paginated) |
| GET | /api/v1/recipes/{id} | Fetch a single recipe |
| GET | /health | Liveness probe — always 200 if process is alive |
| GET | /ready | Readiness probe — 200 only if DB connection is healthy |

Health and readiness probes sit outside the `/api/v1/` prefix so Kubernetes can
reach them without routing through the ingress path rewrite.

---

## Job State Machine

```
[pending] → [processing] → [completed]
                ↓
            [failed]
```

- Job is created as `pending` synchronously in `POST /api/v1/jobs`.
- FastAPI BackgroundTask immediately transitions it to `processing` and runs the pipeline.
- On success: status → `completed`, `recipe_id` populated.
- On failure: status → `failed`, `error` message populated.

> **Note:** FastAPI BackgroundTasks is an intentional demo simplification.
> In a production system this would be replaced by a durable task queue
> (e.g. Celery + Redis or Azure Service Bus) to survive pod restarts and
> support horizontal scaling of workers.

---

## Data Flow

```
User submits URL
  → POST /api/v1/jobs
    → job record created (status: pending)
    → BackgroundTask enqueued
    → return {job_id}

BackgroundTask runs
  → job status → processing
  → TranscriptProvider.fetch(url)      # mock or youtube
  → RecipeExtractor.extract(transcript) # mock or openai
  → recipe record inserted
  → job status → completed, recipe_id set

User polls
  → GET /api/v1/jobs/{id}
    → {status: completed, recipe_id}
  → GET /api/v1/recipes/{recipe_id}
    → full recipe JSON
```

---

## CI/CD Architecture

### Principles
- Build once. The Docker image is built in CI and tagged with the Git commit SHA.
- The same image digest is promoted from dev to prod. No rebuild.
- `latest` is never used in CI/CD pipelines.

### CI — `ci.yml` (runs on every push and PR)

```
Lint (ruff, eslint, tsc)
  → Unit tests (pytest, coverage)
  → Docker build (backend + frontend)
  → Push to ACR tagged with Git SHA   ← only on push to main
  → pip-audit + npm audit
```

### CD — `cd.yml` (runs on successful CI on main)

```
Resolve image SHA from ACR
  → helm diff (show what will change)
  → helm upgrade --install (dev namespace, values-dev.yaml, image tag = Git SHA)
  → Smoke test (curl /health, curl /ready)
  → [manual approval gate]
  → helm upgrade --install (prod namespace, values-prod.yaml, same image SHA)
```

GitHub Actions environments: `dev` (auto-deploy) and `prod` (required reviewer).

---

## Deployment Architecture

```
GitHub Actions
  ├── builds image (SHA-tagged)
  ├── pushes to ACR
  └── helm upgrade → AKS

AKS Cluster
  ├── NGINX Ingress Controller
  ├── frontend pods  (Nginx + React SPA)
  ├── backend pods   (FastAPI + workers)
  └── Secrets Store CSI Driver → Key Vault

Azure PostgreSQL Flexible Server  ← backend connects via private endpoint (prod)
Azure Key Vault                   ← secrets mounted as volumes in pods (prod)
Azure Monitor / App Insights      ← metrics, logs, traces
```

---

## Terraform Module Plan

| Module | Resources |
|---|---|
| `networking` | VNet, subnets (AKS, data, management), NSGs |
| `aks` | AKS cluster, system node pool, managed identity, OIDC issuer |
| `acr` | Azure Container Registry, AcrPull role assignment to AKS identity |
| `postgres` | PostgreSQL Flexible Server, private DNS zone, firewall rules |
| `keyvault` | Key Vault, RBAC assignments, secrets placeholders |
| `monitoring` | Log Analytics Workspace, Application Insights, alert rules |

Environments (`dev`, `prod`) compose these modules with different variable values.
Terraform state stored in Azure Blob Storage (storage account + container per environment).

---

## Observability

| Signal | Tool | Notes |
|---|---|---|
| Metrics | Azure Monitor + Container Insights | Pod, node, cluster metrics — zero extra cluster components |
| Logs | Structured JSON → Log Analytics Workspace | Via Container Insights log collection |
| Traces | OpenTelemetry SDK → Application Insights | `APPLICATIONINSIGHTS_CONNECTION_STRING` env var; added in production-hardening stage |
| Health | `/health` + `/ready` | Wired to Kubernetes liveness/readiness probes in Helm chart |
| Dashboards | Azure Monitor Workbook | Job throughput, error rate, p95 latency |
| Alerts | Azure Monitor alert rules | CrashLoopBackOff > 5 min, error rate threshold |

---

## Production-Hardening Enhancements (do not block initial deployment)

These are real production requirements, tracked explicitly so they are not forgotten.
They are implemented after the initial Azure deployment is stable.

| Enhancement | Description |
|---|---|
| Private endpoints | PostgreSQL and Key Vault accessible only from AKS VNet |
| Workload Identity | OIDC-based pod identity for Key Vault access; replaces any static credentials |
| Key Vault CSI driver | Secrets mounted as volumes; no secrets in Helm values or ConfigMaps |
| cert-manager + TLS | Let's Encrypt certificates via cert-manager on NGINX Ingress |
| OpenTelemetry tracing | OTel SDK in FastAPI, traces exported to Application Insights |
| Non-root containers | Dockerfile USER directive; read-only root filesystem where possible |
| HPA | Horizontal Pod Autoscaler for backend deployment |

---

## Environment Variables Reference

| Variable | Service | Required | Default | Description |
|---|---|---|---|---|
| `DATABASE_URL` | backend | yes | — | PostgreSQL connection string |
| `TRANSCRIPT_PROVIDER` | backend | no | `mock` | `mock` or `youtube` |
| `LLM_PROVIDER` | backend | no | `mock` | `mock` or `openai` |
| `OPENAI_API_KEY` | backend | if `openai` | — | API key for OpenAI or Azure OpenAI |
| `OPENAI_MODEL` | backend | if `openai` | — | Model name e.g. `gpt-4o` |
| `VITE_API_BASE_URL` | frontend | no | `/api/v1` | Override API base URL |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | backend | no | — | Enables OTel trace export |

---

## Security Notes

- No secrets committed to git. `.gitignore` excludes `.env`, `*.tfvars`, `terraform.tfstate*`.
- `.env.example` documents all variables with placeholder values — never real credentials.
- All production secrets live in Azure Key Vault.
- AKS uses Workload Identity (OIDC) for pod-level Key Vault access — no static credentials.
- TLS via cert-manager + Let's Encrypt on NGINX Ingress (production-hardening stage).
- Container images run as non-root (production-hardening stage).
- `pip-audit` and `npm audit` run in every CI pipeline.

---

## What Is Deliberately Out of Scope

| Skipped | Reason |
|---|---|
| Redis / Celery / message broker | BackgroundTasks sufficient at demo scale; documented as simplification |
| Service mesh (Istio / Linkerd) | Adds cluster complexity with no visible demo payoff |
| GitOps (ArgoCD / Flux) | GitHub Actions CD is simpler to explain and sufficient |
| Custom Prometheus + Grafana | Azure Monitor covers the need without extra cluster components |
| Multi-region deployment | One AKS cluster demonstrates the full architecture |
| gRPC | REST is adequate and faster to build |
| Whisper fallback | Future extension only; not needed for the demo |
| GCP portability | Future stage; not in scope for the initial build |
| Ansible | No legitimate config-management use case yet |
| Separate transcript/LLM microservices | Splitting adds k8s complexity without payoff at this scale |

---

## Build Tasks

---

### Day 1 — Local Foundation + Core Pipeline

Goal: The complete application pipeline runs end-to-end on localhost via docker-compose
using mock transcript and LLM providers. No external API credentials required.

---

#### Task 1.1 — Repo Scaffold & Tooling
- **Status:** [ ] pending
- **Intent:** Establish the directory structure, config files, and local developer tooling.
- **Expected Outcomes:**
  - All top-level directories and placeholder files exist
  - `.gitignore` covers Python, Node, Terraform, Docker, and IDE artefacts
  - `.env.example` documents all environment variables
  - `docker-compose.yml` defines `frontend`, `backend`, and `postgres` services with named volumes
  - `backend/requirements.txt` with pinned dependencies
  - `frontend/package.json` with Vite + React + TypeScript
  - `README.md` with project description and local setup steps
- **Todo:**
  1. Create directory structure matching the repository layout above
  2. Write `.gitignore`
  3. Write `.env.example`
  4. Write `docker-compose.yml`
  5. Write `backend/requirements.txt`
  6. Initialise frontend with `npm create vite` (React + TypeScript template)
  7. Write root `README.md`
  8. Initial commit and push to GitHub

---

#### Task 1.2 — Database Models & Migrations
- **Status:** [ ] pending
- **Intent:** Define the PostgreSQL schema and wire Alembic so the DB layer is stable before service logic is written.
- **Expected Outcomes:**
  - `jobs` and `recipes` tables exist after `alembic upgrade head`
  - Models match the data model specification above
  - Alembic env reads `DATABASE_URL` from environment
- **Todo:**
  1. Write `backend/app/db/session.py` and `base.py`
  2. Write `backend/app/models/job.py` and `models/recipe.py`
  3. Initialise Alembic (`alembic init`) and configure `env.py`
  4. Generate and review initial migration
  5. Confirm `alembic upgrade head` runs cleanly against docker-compose postgres

---

#### Task 1.3 — Service Abstractions (TranscriptProvider + RecipeExtractor)
- **Status:** [ ] pending
- **Intent:** Implement both provider abstractions with mock implementations so the full pipeline can run with no external dependencies.
- **Expected Outcomes:**
  - `TranscriptProvider` ABC with `fetch(url: str) -> str`
  - `MockTranscriptProvider` returns a realistic hardcoded cooking transcript string
  - `YouTubeTranscriptProvider` stub (raises `NotImplementedError` with a clear message)
  - `RecipeExtractor` ABC with `extract(transcript: str) -> RecipeSchema`
  - `MockRecipeExtractor` returns a valid hardcoded `RecipeSchema` fixture
  - `OpenAIRecipeExtractor` stub (raises `NotImplementedError` with a clear message)
  - Factory functions `get_transcript_provider()` and `get_recipe_extractor()` read env vars
  - Unit tests for both mocks
- **Todo:**
  1. Write `app/services/transcript/base.py`, `mock.py`, `youtube.py`
  2. Write `app/services/llm/base.py`, `mock.py`, `openai.py`
  3. Write `app/schemas/recipe.py` (Pydantic — used by both extractor and API)
  4. Write factory functions
  5. Write `tests/test_transcript_mock.py` and `tests/test_llm_mock.py`

---

#### Task 1.4 — Recipe Pipeline & API Routes
- **Status:** [ ] pending
- **Intent:** Wire the providers into a pipeline and expose the full API surface.
- **Expected Outcomes:**
  - `POST /api/v1/jobs` creates a job (status: pending), fires BackgroundTask, returns job_id
  - BackgroundTask runs pipeline: fetch transcript → extract recipe → write recipe → update job
  - `GET /api/v1/jobs/{id}` returns current job status and recipe_id when completed
  - `GET /api/v1/recipes` returns paginated recipe list
  - `GET /api/v1/recipes/{id}` returns full recipe
  - `GET /health` returns 200
  - `GET /ready` returns 200 only if DB connection succeeds
  - Integration tests cover the full job lifecycle using mock providers
- **Todo:**
  1. Write `app/schemas/job.py`
  2. Write `app/services/recipe_pipeline.py`
  3. Write `app/api/v1/routes/jobs.py` and `routes/recipes.py`
  4. Write `app/api/v1/router.py` and wire into `main.py`
  5. Add `/health` and `/ready` endpoints directly in `main.py`
  6. Write integration tests in `tests/test_jobs.py` and `tests/test_recipes.py`

---

#### Task 1.5 — React Frontend
- **Status:** [ ] pending
- **Intent:** Build the minimal UI: URL submission, job status polling, and recipe display.
- **Expected Outcomes:**
  - User submits a YouTube URL and sees a loading state
  - App polls `GET /api/v1/jobs/{id}` every 2 seconds until terminal state
  - Recipe card displays all fields (title, ingredients, quantities, equipment, steps, macros)
  - Previous recipes listed below the form
  - Vite dev server proxies `/api` to backend
- **Todo:**
  1. Write `src/types/job.ts` and `types/recipe.ts`
  2. Write `src/hooks/useJobPoller.ts`
  3. Write `src/components/SubmitForm.tsx`
  4. Write `src/components/RecipeCard.tsx`
  5. Write `src/components/RecipeList.tsx`
  6. Write `src/pages/Home.tsx`
  7. Configure Vite proxy in `vite.config.ts`

---

### Day 2 — Containers, IaC, and Kubernetes

Goal: Production Docker images built and pushed to ACR. Azure infrastructure provisioned
with Terraform. Application running on AKS via Helm.

---

#### Task 2.1 — Production Dockerfiles
- **Status:** [ ] pending
- **Intent:** Multi-stage, minimal, non-root Docker images for both services.
- **Expected Outcomes:**
  - `backend/Dockerfile`: multi-stage, non-root user, no dev dependencies in final layer
  - `frontend/Dockerfile`: Node build stage → Nginx serve stage
  - `frontend/nginx.conf`: SPA routing (try_files), `/api` proxy to backend service name
  - Both images build cleanly; docker-compose updated to use them
- **Todo:**
  1. Write `backend/Dockerfile`
  2. Write `frontend/Dockerfile`
  3. Write `frontend/nginx.conf`
  4. Update `docker-compose.yml` to build from Dockerfiles
  5. Verify full stack runs via `docker-compose up --build`

---

#### Task 2.2 — Terraform Modules
- **Status:** [ ] pending
- **Intent:** Reusable modules for each Azure resource type.
- **Expected Outcomes:**
  - Six modules: `networking`, `aks`, `acr`, `postgres`, `keyvault`, `monitoring`
  - Each module has a clean variable interface and output values
  - No environment-specific values inside modules
- **Todo:**
  1. Write `modules/networking/` (VNet, subnets, NSGs)
  2. Write `modules/acr/` (ACR, admin disabled)
  3. Write `modules/postgres/` (PostgreSQL Flexible Server, private DNS zone)
  4. Write `modules/keyvault/` (Key Vault, RBAC mode, soft delete)
  5. Write `modules/aks/` (AKS, managed identity, OIDC issuer enabled)
  6. Write `modules/monitoring/` (Log Analytics Workspace, Application Insights)

---

#### Task 2.3 — Terraform Dev Environment
- **Status:** [ ] pending
- **Intent:** Compose modules into a deployable dev environment and provision Azure infrastructure.
- **Expected Outcomes:**
  - `terraform apply` succeeds for dev environment
  - All six resource types provisioned in Azure
  - AKS managed identity has `AcrPull` role on ACR
  - Terraform state stored in Azure Blob Storage
- **Todo:**
  1. Create Azure storage account and container for Terraform state (manual, one-time)
  2. Write `environments/dev/main.tf` composing all modules
  3. Write `variables.tf`, `terraform.tfvars`, `outputs.tf`
  4. Configure azurerm backend block
  5. Run `terraform init` and `terraform apply`
  6. Record outputs (AKS name, ACR login server, postgres hostname, keyvault URI)

---

#### Task 2.4 — Helm Chart
- **Status:** [ ] pending
- **Intent:** Package the application for parameterised Kubernetes deployment.
- **Expected Outcomes:**
  - `helm lint` and `helm template` produce valid manifests
  - Deployments, Services, Ingress, ConfigMap, HPA, SecretProviderClass all present
  - Image tag is a chart value (set to Git SHA at deploy time, never hardcoded)
  - Secrets referenced from Key Vault via SecretProviderClass — not stored in values files
  - `values-dev.yaml` overrides for dev environment
- **Todo:**
  1. Write `Chart.yaml`
  2. Write `values.yaml` with all configurable defaults
  3. Write deployment templates (frontend, backend)
  4. Write Service and Ingress templates
  5. Write `configmap.yaml` for non-secret env vars
  6. Write `secretproviderclass.yaml` for Key Vault CSI (production-hardening; skip if CSI not yet installed)
  7. Write `hpa.yaml` for backend
  8. Write `values-dev.yaml`
  9. Run `helm lint` and `helm template`

---

#### Task 2.5 — Deploy to AKS
- **Status:** [ ] pending
- **Intent:** Manually deploy to AKS to prove the full path before CI/CD automation.
- **Expected Outcomes:**
  - Images pushed to ACR tagged with current Git SHA
  - `helm upgrade --install` succeeds on dev cluster
  - All pods reach Running state
  - Application reachable via Ingress
  - End-to-end smoke test passes (submit URL, poll job, retrieve recipe — mock providers)
- **Todo:**
  1. Build and push backend + frontend images to ACR (`git rev-parse --short HEAD` as tag)
  2. Configure kubectl context (`az aks get-credentials`)
  3. Install NGINX Ingress Controller on cluster
  4. Install Secrets Store CSI Driver (if production-hardening is in scope for this pass)
  5. Store DB connection string in Key Vault (or use ConfigMap for initial deploy)
  6. Run `helm upgrade --install recipe-lens ./helm/recipe-lens -f values-dev.yaml --set image.tag=<SHA>`
  7. Verify pods, services, ingress
  8. Smoke test end-to-end

---

### Day 3 — CI/CD, Observability, Provider Implementations, and Polish

Goal: Automated pipelines, observability wired up, real transcript and LLM providers
implemented, documentation complete. Project is interview-ready.

---

#### Task 3.1 — GitHub Actions CI Pipeline
- **Status:** [ ] pending
- **Intent:** Automate lint, test, build, and push on every push and PR.
- **Expected Outcomes:**
  - `ci.yml` runs on push to any branch and PRs to `main`
  - Stages: lint → test → docker build → push to ACR (push only on `main`)
  - Backend: `ruff` lint, `pytest --cov`
  - Frontend: `eslint`, `tsc --noEmit`
  - Dependency scanning: `pip-audit`, `npm audit`
  - Images tagged with Git SHA (`github.sha`)
  - ACR credentials via federated identity (OIDC) — no static service principal secrets
- **Todo:**
  1. Write `.github/workflows/ci.yml`
  2. Add `ruff` and `pip-audit` to `requirements.txt`
  3. Add `eslint` config to frontend
  4. Configure GitHub Actions OIDC federated credential on Azure service principal
  5. Add secrets to GitHub: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `ACR_LOGIN_SERVER`
  6. Push a branch and verify pipeline passes

---

#### Task 3.2 — GitHub Actions CD Pipeline
- **Status:** [ ] pending
- **Intent:** Automate Helm deployment to AKS on merge to main, with manual approval for prod.
- **Expected Outcomes:**
  - `cd.yml` triggers after successful CI on `main`
  - Deploys to dev automatically using image SHA from CI
  - Prod deployment requires manual approval (GitHub environment protection)
  - `helm diff` step shows what will change before upgrade
  - Smoke test after each deployment
- **Todo:**
  1. Write `.github/workflows/cd.yml`
  2. Create `dev` and `prod` GitHub environments
  3. Add required reviewer to `prod` environment
  4. Add `helm diff` step
  5. Add smoke test step
  6. Merge a change and verify full CI → CD chain

---

#### Task 3.3 — Observability Wiring
- **Status:** [ ] pending
- **Intent:** Wire metrics, logs, and traces so application health is visible in Azure without extra cluster components.
- **Expected Outcomes:**
  - Container Insights enabled on AKS (pod/node metrics in Azure Monitor)
  - FastAPI emits structured JSON logs captured by Container Insights
  - OTel SDK in FastAPI exports traces to Application Insights (when connection string is set)
  - Liveness and readiness probes configured in Helm chart
  - One Azure Monitor Workbook: job throughput, error rate, p95 latency
  - One alert rule: CrashLoopBackOff > 5 minutes
- **Todo:**
  1. Add Container Insights addon to AKS module in Terraform (Log Analytics workspace ID)
  2. Add `opentelemetry-sdk` and `azure-monitor-opentelemetry-exporter` to `requirements.txt`
  3. Configure OTel in `main.py` (conditional on `APPLICATIONINSIGHTS_CONNECTION_STRING`)
  4. Add structured JSON logging middleware to FastAPI
  5. Update Helm chart: liveness probe (`/health`), readiness probe (`/ready`)
  6. Create Azure Monitor Workbook (portal → export JSON → commit to `infra/monitoring/`)
  7. Add alert rule to `modules/monitoring/`

---

#### Task 3.4 — YouTubeTranscriptProvider Implementation
- **Status:** [ ] pending
- **Intent:** Implement the real transcript provider so it can be activated by changing one env var.
- **Expected Outcomes:**
  - `YouTubeTranscriptProvider.fetch(url)` returns plain-text transcript using `youtube-transcript-api`
  - Raises `TranscriptUnavailableError` for videos with no transcript
  - Setting `TRANSCRIPT_PROVIDER=youtube` activates it; no code changes required
  - Unit test covers happy path and unavailable case with mocked API
- **Todo:**
  1. Implement `app/services/transcript/youtube.py`
  2. Define `TranscriptUnavailableError` in `base.py`
  3. Write unit test with mocked `youtube-transcript-api` response
  4. Test manually with a real YouTube cooking video URL

---

#### Task 3.5 — OpenAIRecipeExtractor Implementation
- **Status:** [ ] pending
- **Intent:** Implement the real LLM provider ready to activate the moment an API key is available.
- **Expected Outcomes:**
  - `OpenAIRecipeExtractor.extract(transcript)` calls OpenAI API and returns `RecipeSchema`
  - Reads `OPENAI_API_KEY` and `OPENAI_MODEL` from environment — nothing hardcoded
  - Structured prompt instructs the model to return JSON matching `RecipeSchema`
  - Response parsed and validated with Pydantic
  - Setting `LLM_PROVIDER=openai` activates it; no code changes required
  - Unit test mocks the HTTP call and validates schema parsing
- **Todo:**
  1. Implement `app/services/llm/openai.py`
  2. Write system prompt and user prompt template
  3. Add JSON response parsing with Pydantic validation
  4. Add `openai` to `requirements.txt`
  5. Write unit test with mocked `openai` client
  6. Document activation steps in `README.md`

---

#### Task 3.6 — Documentation & Interview Readiness
- **Status:** [ ] pending
- **Intent:** Ensure the project tells a clear, confident story to a technical interviewer.
- **Expected Outcomes:**
  - `README.md` covers: purpose, local setup, environment variables, CI/CD overview, infrastructure overview, LLM activation steps
  - Architecture diagram in README
  - Environment variable reference table
  - "Plugging in a real LLM" section
  - "Infrastructure provisioning" quick-start
  - All production-hardening items documented as known next steps
- **Todo:**
  1. Rewrite `README.md` with all sections above
  2. Add architecture diagram (Mermaid)
  3. Add environment variable table
  4. Add "Plugging in a real LLM provider" section
  5. Add "Production hardening" section listing next steps
  6. Final review: confirm no secrets, no hardcoded values, no TODO comments in committed code

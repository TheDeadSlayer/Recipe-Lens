# RecipeLens Frontend — Build Plan

## Overview

Build a polished React + TypeScript + Vite SPA for RecipeLens. The frontend connects
to the existing FastAPI backend via its REST API. The goal is a credible food-tech /
AI SaaS product suitable for a technical interview, not a developer demo.

Three routes: `/` (Analyze), `/recipes` (library), `/recipes/:id` (detail).
No auth. No Redux. No large UI frameworks. Tailwind CSS for styling.

---

## 1. Actual API Contracts

### POST /api/v1/jobs
**Request body:**
```json
{ "source_url": "https://www.youtube.com/watch?v=..." }
```
**Response 202:**
```json
{
  "id": "uuid",
  "source_url": "https://...",
  "status": "pending",
  "recipe_id": null,
  "error_message": null,
  "classification_reason": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### GET /api/v1/jobs/{job_id}
**Response 200 — terminal states:**

`completed`:
```json
{
  "id": "uuid",
  "status": "completed",
  "recipe_id": "uuid",
  "error_message": null,
  "classification_reason": null,
  ...
}
```

`not_recipe`:
```json
{
  "status": "not_recipe",
  "recipe_id": null,
  "error_message": null,
  "classification_reason": "This is a restaurant review with no preparation instructions.",
  ...
}
```

`failed`:
```json
{
  "status": "failed",
  "recipe_id": null,
  "error_message": "Gemini API error ...",
  "classification_reason": null,
  ...
}
```

`pending` / `processing` — keep polling.

### GET /api/v1/recipes?skip=0&limit=20
**Response 200:**
```json
[
  {
    "id": "uuid",
    "job_id": "uuid",
    "source_url": "https://...",
    "title": "Sheet-Pan Chicken",
    "description": "Easy one-pan weeknight dinner.",
    "ingredients": [{ "name": "Chicken thighs", "quantity": "4 pieces" }],
    "equipment": ["Sheet pan", "Oven"],
    "steps": ["Preheat oven to 200°C.", "..."],
    "calories": 420,
    "protein_g": 38.0,
    "carbs_g": 2.0,
    "fat_g": 28.0,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

Nutrition fields are `number | null`. `description` is `string | null`. `equipment` is
`string[]` (may be empty). `ingredients[].quantity` is always a string.

### GET /api/v1/recipes/{id}
Same shape as list item above.

---

## 2. Backend Changes Required

### 2a. CORS
`backend/app/main.py` has **no CORSMiddleware**. The browser will block all requests
from `http://localhost:5173` to `http://localhost:8000` without it.

Add `CORSMiddleware` reading allowed origins from a new `CORS_ORIGINS` env var.
Default for local dev: `http://localhost:5173` (Vite dev server default port).

### 2b. Settings
Add `cors_origins: list[str]` to `backend/app/core/config.py`, defaulting to
`["http://localhost:5173"]`.

### 2c. .env.example
Add `CORS_ORIGINS=http://localhost:5173,http://localhost:3000` entry.

### 2d. Docker Compose
- Add `frontend` service using a new `frontend/Dockerfile`.
- Add `CORS_ORIGINS=http://localhost:5173` to the `backend` service environment.
- Vite dev server runs on port 5173; expose it.
- Frontend container needs `VITE_API_BASE_URL=http://localhost:8000` so the browser
  (not the container) can reach the backend.

---

## 3. Frontend Architecture

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts          # base fetch wrapper, reads VITE_API_BASE_URL
│   │   ├── jobs.ts            # createJob(), getJob()
│   │   └── recipes.ts         # listRecipes(), getRecipe()
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx     # nav: RecipeLens | Analyze | Recipes (active highlight)
│   │   │   └── PageContainer.tsx
│   │   ├── analyze/
│   │   │   ├── VideoUrlForm.tsx    # URL input + validate + submit
│   │   │   ├── VideoPlayer.tsx     # YouTube iframe embed
│   │   │   ├── AnalysisStatus.tsx  # pending/processing/not_recipe/failed states
│   │   │   └── AnalysisResult.tsx  # completed recipe display
│   │   └── recipes/
│   │       ├── RecipeCard.tsx      # card for grid
│   │       ├── RecipeGrid.tsx      # responsive grid + empty state
│   │       ├── IngredientList.tsx  # ingredient bullet list
│   │       ├── RecipeSteps.tsx     # numbered steps
│   │       └── NutritionSummary.tsx # compact stat cards
│   ├── pages/
│   │   ├── AnalyzePage.tsx
│   │   ├── RecipesPage.tsx
│   │   └── RecipeDetailPage.tsx
│   ├── types/
│   │   └── api.ts             # Job, Recipe, Ingredient interfaces — typed to backend
│   ├── utils/
│   │   └── youtube.ts         # extractVideoId(), embedUrl(), thumbnailUrl()
│   ├── App.tsx                # Router + Header + route definitions
│   └── main.tsx
├── .env.example
├── Dockerfile
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

**State management:** local `useState` / `useEffect` only. No external state library.

**Polling:** `useEffect` with `setInterval` + cleanup. Poll every 2 s. Stop on terminal
state (`completed`, `not_recipe`, `failed`). Clean up on unmount.

**Routing:** React Router v6 `createBrowserRouter` / `<Outlet>`.

---

## 4. Visual / Component Structure

### Color palette (Tailwind)
- Background: `slate-50` / white
- Text: `slate-900` primary, `slate-500` muted
- Accent: `amber-500` / `amber-600` (food/warm tone)
- Border: `slate-200`
- Card: white with `shadow-sm` and `rounded-xl`
- Status success: `emerald-600`
- Status error: `red-600`
- Status warning / not_recipe: `amber-600`

### Typography
- Logo: `font-bold text-slate-900` with amber accent dot or spark icon
- Hero heading: `text-4xl font-bold tracking-tight`
- Section headings: `text-xl font-semibold`
- Body: `text-slate-600`

### AnalyzePage layout (desktop)
After submission, transitions from single-column hero into two-column:
- Left: `aspect-video` YouTube iframe (16:9, rounded, shadow)
- Right: processing status panel or completed recipe result
- On mobile: stacked vertically

### RecipesPage
- Responsive grid: 1 col mobile → 2 col md → 3 col lg
- Each card: thumbnail (YouTube `hqdefault.jpg` or placeholder), title, description
  snippet, compact nutrition row, "View Recipe" link
- Empty state: centered icon + heading + CTA button
- Client-side title filter input above grid

### RecipeDetailPage
- Full-width header: title + description + nutrition cards row
- Two-column body (md+): left = ingredients + equipment, right = steps
- Below fold: YouTube player (source video)
- Mobile: single column, player at bottom

---

## Sub-Tasks

---

### Task 1 — Backend: CORS + Settings
**Intent:** Make the API accessible from the browser without weakening security.
**Expected Outcomes:**
- `GET /api/v1/recipes` works from `http://localhost:5173` without CORS errors
- `CORS_ORIGINS` is an env var with sensible default
- `.env.example` updated
**Todo:**
1. Add `cors_origins: list[str]` to `Settings` in `backend/app/core/config.py`
   Default: `["http://localhost:5173"]`
2. Add `CORSMiddleware` in `backend/app/main.py` using `settings.cors_origins`
3. Add `CORS_ORIGINS=http://localhost:5173` to `.env.example`
**Relevant context:** `backend/app/core/config.py`, `backend/app/main.py`
**Status:** [ ] pending

---

### Task 2 — Frontend Scaffold
**Intent:** Create the Vite + React + TypeScript + Tailwind project with routing and dev tooling.
**Expected Outcomes:**
- `npm run dev` serves the app at `http://localhost:5173`
- `npm run build` compiles without errors
- `npm run typecheck` passes
- React Router, Tailwind, Lucide React all installed and configured
- `frontend/.env.example` documents `VITE_API_BASE_URL`
**Todo:**
1. Create `frontend/` directory with `package.json` (Vite + React + TypeScript template dependencies)
2. Create `vite.config.ts` — no proxy needed (frontend calls backend directly via `VITE_API_BASE_URL`)
3. Create `tailwind.config.js` and `postcss.config.js`
4. Create `tsconfig.json` — strict mode, no `any`
5. Create `index.html`
6. Create `frontend/.env.example` with `VITE_API_BASE_URL=http://localhost:8000`
7. Create `src/main.tsx` entry point
8. Create `src/App.tsx` with React Router routes and Header
**Relevant context:** React Router v6, Vite, Tailwind CSS v3
**Status:** [ ] pending

---

### Task 3 — Types + API Layer
**Intent:** Typed interfaces matching backend schemas; centralized fetch wrappers.
**Expected Outcomes:**
- `src/types/api.ts` has `Job`, `Recipe`, `Ingredient` interfaces — zero `any`
- `src/api/client.ts` reads `VITE_API_BASE_URL`, throws typed errors
- `src/api/jobs.ts` exports `createJob(url)`, `getJob(id)`
- `src/api/recipes.ts` exports `listRecipes(skip, limit)`, `getRecipe(id)`
**Todo:**
1. Write `src/types/api.ts` mirroring `JobRead`, `RecipeRead`, `Ingredient` exactly
2. Write `src/api/client.ts` base wrapper
3. Write `src/api/jobs.ts`
4. Write `src/api/recipes.ts`
**Relevant context:** `backend/app/schemas/job.py`, `backend/app/schemas/recipe.py`
**Status:** [ ] pending

---

### Task 4 — YouTube Utility
**Intent:** One place for all YouTube URL/ID logic; reused by embed, thumbnails, validation.
**Expected Outcomes:**
- `extractVideoId(url)` correctly handles `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/`
- `embedUrl(videoId)` returns `https://www.youtube.com/embed/{id}`
- `thumbnailUrl(videoId)` returns `https://img.youtube.com/vi/{id}/hqdefault.jpg`
- `isValidYouTubeUrl(url)` returns boolean
**Todo:**
1. Write `src/utils/youtube.ts` with all four functions
**Relevant context:** YouTube URL formats listed in spec
**Status:** [ ] pending

---

### Task 5 — Layout Components
**Intent:** Shared Header with nav and PageContainer for consistent layout.
**Expected Outcomes:**
- Header shows RecipeLens brand + Analyze + Recipes nav links
- Active route highlighted with amber accent
- Header is fully responsive (hamburger or inline nav on mobile)
- PageContainer provides consistent max-width and padding
**Todo:**
1. Write `src/components/layout/Header.tsx`
2. Write `src/components/layout/PageContainer.tsx`
**Relevant context:** React Router `useLocation` for active link detection
**Status:** [ ] pending

---

### Task 6 — Analyze Page
**Intent:** Main page with hero, URL form, video player, polling, and result display.
**Expected Outcomes:**
- Hero section renders on initial load
- URL input validates YouTube format before enabling submit
- Submitting transitions to two-column layout (video left, status right)
- Polls every 2 s; stops on terminal state; cleans up on unmount
- Completed: shows full recipe result inline
- not_recipe: shows friendly "No recipe detected" panel with classification_reason
- failed: shows professional error state without exposing stack traces
- Duplicate submit prevented while job is active
**Todo:**
1. Write `src/components/analyze/VideoUrlForm.tsx`
2. Write `src/components/analyze/VideoPlayer.tsx` (YouTube iframe)
3. Write `src/components/analyze/AnalysisStatus.tsx` (pending/processing/not_recipe/failed)
4. Write `src/components/analyze/AnalysisResult.tsx` (completed recipe)
5. Write `src/pages/AnalyzePage.tsx` composing all analyze components
**Relevant context:** job statuses: `pending`, `processing`, `completed`, `not_recipe`, `failed`
**Status:** [ ] pending

---

### Task 7 — Recipe Components + Shared Display
**Intent:** Reusable recipe display components used by both AnalysisResult and RecipeDetailPage.
**Expected Outcomes:**
- `IngredientList` renders name + quantity, never shows null/undefined
- `RecipeSteps` renders numbered steps
- `NutritionSummary` renders only fields with actual values as stat cards
- Equipment list only renders when non-empty
**Todo:**
1. Write `src/components/recipes/IngredientList.tsx`
2. Write `src/components/recipes/RecipeSteps.tsx`
3. Write `src/components/recipes/NutritionSummary.tsx`
**Relevant context:** `RecipeRead` schema — all optional fields may be null or empty
**Status:** [ ] pending

---

### Task 8 — Recipes Library Page
**Intent:** `/recipes` — grid of stored recipes with empty state and client-side filter.
**Expected Outcomes:**
- Fetches `GET /api/v1/recipes` on mount
- Responsive 1→2→3 column card grid
- Each card shows thumbnail (YouTube hqdefault or placeholder), title, description, nutrition, link
- Empty state with CTA
- Client-side filter input above grid
- Error state for fetch failure
**Todo:**
1. Write `src/components/recipes/RecipeCard.tsx`
2. Write `src/components/recipes/RecipeGrid.tsx` (grid + empty state + filter)
3. Write `src/pages/RecipesPage.tsx`
**Relevant context:** `listRecipes()` API call, `thumbnailUrl()` utility
**Status:** [ ] pending

---

### Task 9 — Recipe Detail Page
**Intent:** `/recipes/:id` — full recipe view with two-column layout and embedded video.
**Expected Outcomes:**
- Fetches `GET /api/v1/recipes/{id}` on mount
- Desktop: two-column (ingredients+equipment left, steps right)
- Mobile: single column
- YouTube player below the recipe for source video
- Loading state, 404 state
**Todo:**
1. Write `src/pages/RecipeDetailPage.tsx`
**Relevant context:** `getRecipe()` API, `VideoPlayer` component
**Status:** [ ] pending

---

### Task 10 — Docker Compose + Frontend Dockerfile
**Intent:** `docker compose up` starts all three services with correct networking.
**Expected Outcomes:**
- `docker compose up` starts postgres + backend + frontend
- Frontend container serves Vite dev server on port 5173
- `VITE_API_BASE_URL=http://localhost:8000` set so the browser can reach the backend
- Backend has `CORS_ORIGINS=http://localhost:5173`
**Todo:**
1. Write `frontend/Dockerfile` (Node 20, `npm run dev`, expose 5173)
2. Update `docker-compose.yml`: add `frontend` service, add CORS env to backend
3. Ensure Vite dev server binds to `0.0.0.0` inside the container (add `--host` flag)
**Relevant context:** Vite `--host` flag required for Docker; `VITE_API_BASE_URL` is a
browser-side env var (must be `localhost`, not the Docker service hostname)
**Status:** [ ] pending

---

### Task 11 — Tests
**Intent:** Vitest + React Testing Library covering all specified scenarios.
**Expected Outcomes:**
- YouTube URL parsing tests: all three formats, invalid URLs
- Form submission: valid URL → submit enabled; invalid → disabled
- Job polling state machine: pending/processing/completed/not_recipe/failed
- Optional field handling: null macros, null description, empty equipment
- Recipes library: populated grid, empty state
- All tests pass; `npm run build` and `tsc --noEmit` succeed
**Todo:**
1. Add Vitest, `@testing-library/react`, `@testing-library/user-event`, `jsdom` to devDependencies
2. Configure Vitest in `vite.config.ts`
3. Write `src/utils/youtube.test.ts`
4. Write `src/pages/AnalyzePage.test.tsx`
5. Write `src/pages/RecipesPage.test.tsx`
**Relevant context:** All mocks via `vi.mock`; no real network calls in tests
**Status:** [ ] pending

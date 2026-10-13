import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AnalyzePage from '../pages/AnalyzePage'
import type { Job, JobCreateResponse, Recipe } from '../types/api'

// ── Mocks ─────────────────────────────────────────────────────────────────────
vi.mock('../api/jobs', () => ({
  createJob: vi.fn(),
  getJob: vi.fn(),
}))
vi.mock('../api/recipes', () => ({
  getRecipe: vi.fn(),
  listRecipes: vi.fn(),
}))

import { createJob, getJob } from '../api/jobs'
import { getRecipe } from '../api/recipes'

const mockCreateJob = vi.mocked(createJob)
const mockGetJob = vi.mocked(getJob)
const mockGetRecipe = vi.mocked(getRecipe)

const VALID_URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
const INVALID_URL = 'https://example.com/video'

function makePendingJob(overrides: Partial<Job> = {}): Job {
  return {
    id: 'job-1',
    source_url: VALID_URL,
    status: 'pending',
    recipe_id: null,
    error_message: null,
    classification_reason: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

/** New job response (not a duplicate). */
function makeNewJobResponse(jobId = 'job-1'): JobCreateResponse {
  return {
    already_exists: false,
    job_id: jobId,
    recipe_id: null,
    recipe: null,
  }
}

/** Duplicate video response (Layer 1 dedup hit). */
function makeAlreadyExistsResponse(recipe: Recipe): JobCreateResponse {
  return {
    already_exists: true,
    job_id: null,
    recipe_id: recipe.id,
    recipe,
  }
}

function makeRecipe(overrides: Partial<Recipe> = {}): Recipe {
  return {
    id: 'recipe-1',
    job_id: 'job-1',
    source_url: VALID_URL,
    source_video_id: 'dQw4w9WgXcQ',
    title: 'Test Recipe',
    description: 'A tasty dish.',
    ingredients: [{ name: 'Egg', quantity: '2' }],
    equipment: ['Pan'],
    steps: ['Crack egg.', 'Cook.'],
    calories: 300,
    protein_g: 20,
    carbs_g: 10,
    fat_g: 15,
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

function renderPage() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AnalyzePage />
    </MemoryRouter>,
  )
}

function typeUrl(url: string) {
  const input = screen.getByRole('textbox')
  fireEvent.change(input, { target: { value: url } })
}

function clickSubmit() {
  fireEvent.click(screen.getByRole('button', { name: /analyze recipe/i }))
}

beforeEach(() => {
  // Use real timers — fake timers break waitFor's internal setTimeout.
  // Poll interval is 2 s; tests control job state via mock return values.
  vi.useRealTimers()
})

afterEach(() => {
  vi.clearAllMocks()
})

// ── Hero / form validation ─────────────────────────────────────────────────────
describe('AnalyzePage hero', () => {
  it('renders hero heading on initial load', () => {
    renderPage()
    expect(
      screen.getByRole('heading', { name: /turn cooking videos/i }),
    ).toBeInTheDocument()
  })

  it('submit button is disabled for invalid URL', () => {
    renderPage()
    typeUrl(INVALID_URL)
    expect(screen.getByRole('button', { name: /analyze recipe/i })).toBeDisabled()
  })

  it('submit button is enabled for valid YouTube URL', () => {
    renderPage()
    typeUrl(VALID_URL)
    expect(screen.getByRole('button', { name: /analyze recipe/i })).toBeEnabled()
  })

  it('shows validation error for non-YouTube URL', () => {
    renderPage()
    typeUrl(INVALID_URL)
    expect(screen.getByRole('alert')).toHaveTextContent(/valid youtube url/i)
  })
})

// ── Processing states ──────────────────────────────────────────────────────────
// These tests mock the interval tick directly so no real 2-second delays occur.
// We override setInterval to capture the callback, then call it manually.
describe('AnalyzePage processing', () => {
  it('shows processing state while job is pending/processing', async () => {
    mockCreateJob.mockResolvedValue(makeNewJobResponse())
    // getJob always returns processing so polling never terminates — fine for this test
    mockGetJob.mockResolvedValue(makePendingJob({ status: 'processing' }))

    renderPage()
    typeUrl(VALID_URL)
    clickSubmit()

    await waitFor(() =>
      expect(screen.getByText(/analyzing your video/i)).toBeInTheDocument(),
    )
  })

  it('shows completed recipe when job completes', async () => {
    const recipe = makeRecipe()
    mockCreateJob.mockResolvedValue(makeNewJobResponse())
    // First poll → processing, subsequent polls → completed
    mockGetJob
      .mockResolvedValueOnce(makePendingJob({ status: 'processing' }))
      .mockResolvedValue(makePendingJob({ status: 'completed', recipe_id: 'recipe-1' }))
    mockGetRecipe.mockResolvedValue(recipe)

    renderPage()
    typeUrl(VALID_URL)
    clickSubmit()

    // Wait for polling to advance to completed; each poll is 2 s real time but
    // mockResolvedValue resolves immediately so waitFor converges quickly.
    await waitFor(
      () => expect(screen.getByText('Test Recipe')).toBeInTheDocument(),
      { timeout: 10_000 },
    )
  })

  it('extraction never called when classification is not_recipe', async () => {
    const notRecipeJob = makePendingJob({
      status: 'not_recipe',
      classification_reason: 'This is a food review.',
    })
    mockCreateJob.mockResolvedValue(makeNewJobResponse())
    mockGetJob.mockResolvedValue(notRecipeJob)

    renderPage()
    typeUrl(VALID_URL)
    clickSubmit()

    await waitFor(
      () => expect(screen.getByText(/no recipe detected/i)).toBeInTheDocument(),
      { timeout: 10_000 },
    )
    expect(mockGetRecipe).not.toHaveBeenCalled()
  })

  it('shows classification reason for not_recipe result', async () => {
    const reason = 'This is a mukbang eating video.'
    mockCreateJob.mockResolvedValue(makeNewJobResponse())
    mockGetJob.mockResolvedValue(
      makePendingJob({ status: 'not_recipe', classification_reason: reason }),
    )

    renderPage()
    typeUrl(VALID_URL)
    clickSubmit()

    await waitFor(
      () => expect(screen.getByText(`"${reason}"`)).toBeInTheDocument(),
      { timeout: 10_000 },
    )
  })

  it('shows failed state when job fails', async () => {
    mockCreateJob.mockResolvedValue(makeNewJobResponse())
    mockGetJob.mockResolvedValue(
      makePendingJob({ status: 'failed', error_message: 'Gemini internal error stack trace' }),
    )

    renderPage()
    typeUrl(VALID_URL)
    clickSubmit()

    await waitFor(
      () => expect(screen.getByText(/couldn't analyze this video/i)).toBeInTheDocument(),
      { timeout: 10_000 },
    )
    // Raw error message / stack trace must not be shown in the UI
    expect(screen.queryByText(/Gemini internal error/i)).not.toBeInTheDocument()
  })
})

// ── Already-exists (Layer 1 dedup) ─────────────────────────────────────────────
describe('AnalyzePage already_exists', () => {
  it('shows already-in-your-recipes banner for duplicate video', async () => {
    const recipe = makeRecipe()
    mockCreateJob.mockResolvedValue(makeAlreadyExistsResponse(recipe))

    renderPage()
    typeUrl(VALID_URL)
    clickSubmit()

    await waitFor(
      () => expect(screen.getByText(/already in your recipes/i)).toBeInTheDocument(),
      { timeout: 5_000 },
    )
    // Recipe is rendered immediately
    expect(screen.getByText('Test Recipe')).toBeInTheDocument()
  })

  it('does not start polling when already_exists', async () => {
    const recipe = makeRecipe()
    mockCreateJob.mockResolvedValue(makeAlreadyExistsResponse(recipe))

    renderPage()
    typeUrl(VALID_URL)
    clickSubmit()

    await waitFor(
      () => expect(screen.getByText(/already in your recipes/i)).toBeInTheDocument(),
      { timeout: 5_000 },
    )
    // getJob (polling) must never be called for an already_exists hit
    expect(mockGetJob).not.toHaveBeenCalled()
  })

  it('shows view-recipe link pointing to the existing recipe', async () => {
    const recipe = makeRecipe({ id: 'recipe-existing-42' })
    mockCreateJob.mockResolvedValue(makeAlreadyExistsResponse(recipe))

    renderPage()
    typeUrl(VALID_URL)
    clickSubmit()

    await waitFor(
      () => expect(screen.getByText(/view recipe/i)).toBeInTheDocument(),
      { timeout: 5_000 },
    )
    const link = screen.getByRole('link', { name: /view recipe/i })
    expect(link).toHaveAttribute('href', '/recipes/recipe-existing-42')
  })
})

// ── Optional field handling ────────────────────────────────────────────────────
describe('AnalyzePage optional recipe fields', () => {
  async function renderWithRecipe(overrides: Partial<Recipe>) {
    const recipe = makeRecipe(overrides)
    mockCreateJob.mockResolvedValue(makeNewJobResponse())
    mockGetJob.mockResolvedValue(
      makePendingJob({ status: 'completed', recipe_id: 'recipe-1' }),
    )
    mockGetRecipe.mockResolvedValue(recipe)

    renderPage()
    typeUrl(VALID_URL)
    clickSubmit()

    await waitFor(
      () => expect(screen.getByText(recipe.title)).toBeInTheDocument(),
      { timeout: 10_000 },
    )
  }

  it('succeeds when all macros are null', async () => {
    await renderWithRecipe({ calories: null, protein_g: null, carbs_g: null, fat_g: null })
    expect(screen.queryByText('null')).not.toBeInTheDocument()
    expect(screen.queryByText('undefined')).not.toBeInTheDocument()
  })

  it('succeeds when description is null', async () => {
    await renderWithRecipe({ description: null })
    expect(screen.queryByText('null')).not.toBeInTheDocument()
  })

  it('succeeds when equipment is empty', async () => {
    await renderWithRecipe({ equipment: [] })
    // Equipment heading must not render when list is empty
    expect(screen.queryByText('Equipment')).not.toBeInTheDocument()
  })
})

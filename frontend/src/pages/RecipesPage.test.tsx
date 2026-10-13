import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import RecipesPage from '../pages/RecipesPage'
import type { Recipe } from '../types/api'

vi.mock('../api/recipes', () => ({
  listRecipes: vi.fn(),
  getRecipe: vi.fn(),
}))

import { listRecipes } from '../api/recipes'
const mockListRecipes = vi.mocked(listRecipes)

function makeRecipe(id: string, title: string, overrides: Partial<Recipe> = {}): Recipe {
  return {
    id,
    job_id: 'job-1',
    source_url: `https://www.youtube.com/watch?v=${id}`,
    title,
    description: 'A delicious recipe.',
    ingredients: [{ name: 'Flour', quantity: '200g' }],
    equipment: ['Bowl'],
    steps: ['Mix.'],
    calories: 400,
    protein_g: 20,
    carbs_g: 50,
    fat_g: 10,
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

function renderPage() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <RecipesPage />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('RecipesPage', () => {
  it('shows loading skeleton initially', () => {
    mockListRecipes.mockReturnValue(new Promise(() => {})) // never resolves
    renderPage()
    expect(screen.getByLabelText(/loading recipes/i)).toBeInTheDocument()
  })

  it('renders recipe cards after loading', async () => {
    mockListRecipes.mockResolvedValue([
      makeRecipe('abc', 'Pasta Carbonara'),
      makeRecipe('def', 'Sheet-Pan Chicken'),
    ])
    renderPage()
    await waitFor(() =>
      expect(screen.getByText('Pasta Carbonara')).toBeInTheDocument(),
    )
    expect(screen.getByText('Sheet-Pan Chicken')).toBeInTheDocument()
  })

  it('shows empty state when no recipes exist', async () => {
    mockListRecipes.mockResolvedValue([])
    renderPage()
    await waitFor(() =>
      expect(screen.getByText(/no recipes yet/i)).toBeInTheDocument(),
    )
    expect(
      screen.getByRole('link', { name: /analyze a video/i }),
    ).toBeInTheDocument()
  })

  it('shows error state on fetch failure', async () => {
    mockListRecipes.mockRejectedValue(new Error('Network error'))
    renderPage()
    await waitFor(() =>
      expect(screen.getByText(/failed to load recipes/i)).toBeInTheDocument(),
    )
  })

  it('does not render null or undefined for missing optional fields', async () => {
    mockListRecipes.mockResolvedValue([
      makeRecipe('abc', 'Simple Recipe', {
        description: null,
        calories: null,
        protein_g: null,
        carbs_g: null,
        fat_g: null,
      }),
    ])
    renderPage()
    await waitFor(() =>
      expect(screen.getByText('Simple Recipe')).toBeInTheDocument(),
    )
    expect(screen.queryByText('null')).not.toBeInTheDocument()
    expect(screen.queryByText('undefined')).not.toBeInTheDocument()
  })
})

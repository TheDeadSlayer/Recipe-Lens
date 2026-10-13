import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Search, UtensilsCrossed } from 'lucide-react'
import PageContainer from '../components/layout/PageContainer'
import RecipeCard from '../components/recipes/RecipeCard'
import { listRecipes } from '../api/recipes'
import type { Recipe } from '../types/api'

export default function RecipesPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    listRecipes()
      .then((data) => {
        if (!cancelled) {
          setRecipes(data)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load recipes. Please try again.')
          setLoading(false)
        }
      })
    return () => { cancelled = true }
  }, [])

  const filtered = filter.trim()
    ? recipes.filter((r) =>
        r.title.toLowerCase().includes(filter.toLowerCase()),
      )
    : recipes

  return (
    <PageContainer>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight mb-1">
          Your Recipes
        </h1>
        <p className="text-slate-500 text-sm">
          Recipes extracted and saved by RecipeLens.
        </p>
      </div>

      {/* Filter */}
      {recipes.length > 0 && (
        <div className="relative mb-6 max-w-xs">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            aria-hidden="true"
          />
          <input
            type="search"
            placeholder="Filter by title…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 text-sm rounded-xl border border-slate-300 bg-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400"
            aria-label="Filter recipes by title"
          />
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
          aria-busy="true"
          aria-label="Loading recipes"
        >
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-2xl border border-slate-200 overflow-hidden"
            >
              <div className="aspect-video bg-slate-100 animate-pulse" />
              <div className="p-5 space-y-3">
                <div className="h-4 bg-slate-100 rounded animate-pulse w-3/4" />
                <div className="h-3 bg-slate-100 rounded animate-pulse w-1/2" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && recipes.length === 0 && (
        <div className="flex flex-col items-center justify-center text-center py-24">
          <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center mb-5">
            <UtensilsCrossed size={28} className="text-amber-400" aria-hidden="true" />
          </div>
          <h2 className="text-xl font-semibold text-slate-900 mb-2">
            No recipes yet
          </h2>
          <p className="text-sm text-slate-500 mb-6 max-w-xs">
            Analyze your first cooking video to build your collection.
          </p>
          <Link
            to="/"
            className="px-5 py-2.5 rounded-xl bg-amber-500 text-white text-sm font-semibold hover:bg-amber-600 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2"
          >
            Analyze a video
          </Link>
        </div>
      )}

      {/* Filter empty */}
      {!loading && !error && recipes.length > 0 && filtered.length === 0 && (
        <p className="text-sm text-slate-500 py-8 text-center">
          No recipes match "{filter}".
        </p>
      )}

      {/* Grid */}
      {!loading && !error && filtered.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((recipe) => (
            <RecipeCard key={recipe.id} recipe={recipe} />
          ))}
        </div>
      )}
    </PageContainer>
  )
}

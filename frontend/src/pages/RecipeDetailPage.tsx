import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, ExternalLink } from 'lucide-react'
import PageContainer from '../components/layout/PageContainer'
import VideoPlayer from '../components/analyze/VideoPlayer'
import IngredientList from '../components/recipes/IngredientList'
import RecipeSteps from '../components/recipes/RecipeSteps'
import NutritionSummary from '../components/recipes/NutritionSummary'
import { getRecipe } from '../api/recipes'
import { extractVideoId } from '../utils/youtube'
import type { Recipe } from '../types/api'

export default function RecipeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setLoading(true)
    getRecipe(id)
      .then((data) => {
        if (!cancelled) {
          setRecipe(data)
          setLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return
        if (
          err instanceof Error &&
          err.constructor.name === 'ApiError' &&
          (err as { status?: number }).status === 404
        ) {
          setNotFound(true)
        } else {
          setError('Failed to load recipe.')
        }
        setLoading(false)
      })
    return () => { cancelled = true }
  }, [id])

  if (loading) {
    return (
      <PageContainer>
        <div className="space-y-6 animate-pulse">
          <div className="h-8 bg-slate-100 rounded-lg w-1/2" />
          <div className="h-4 bg-slate-100 rounded w-1/3" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 bg-slate-100 rounded-xl" />
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-4 bg-slate-100 rounded" />
              ))}
            </div>
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-10 bg-slate-100 rounded" />
              ))}
            </div>
          </div>
        </div>
      </PageContainer>
    )
  }

  if (notFound) {
    return (
      <PageContainer>
        <div className="text-center py-20">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Recipe not found</h1>
          <p className="text-slate-500 mb-6 text-sm">
            This recipe may have been removed or the link is incorrect.
          </p>
          <Link
            to="/recipes"
            className="inline-flex items-center gap-2 text-sm text-amber-600 font-semibold hover:text-amber-700"
          >
            <ArrowLeft size={14} />
            Back to recipes
          </Link>
        </div>
      </PageContainer>
    )
  }

  if (error || !recipe) {
    return (
      <PageContainer>
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error ?? 'Something went wrong.'}
        </div>
      </PageContainer>
    )
  }

  const videoId = extractVideoId(recipe.source_url)

  return (
    <PageContainer>
      {/* Breadcrumb */}
      <Link
        to="/recipes"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6 transition-colors"
      >
        <ArrowLeft size={14} />
        All recipes
      </Link>

      {/* Title + description */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight leading-tight mb-2">
          {recipe.title}
        </h1>
        {recipe.description && (
          <p className="text-slate-500 leading-relaxed max-w-2xl">
            {recipe.description}
          </p>
        )}
      </div>

      {/* Nutrition */}
      <div className="mb-8">
        <NutritionSummary recipe={recipe} />
      </div>

      {/* Two-column body */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
        {/* Left: ingredients + equipment */}
        <section aria-labelledby="ingredients-heading">
          <h2
            id="ingredients-heading"
            className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4"
          >
            Ingredients
          </h2>
          <IngredientList ingredients={recipe.ingredients} />

          {recipe.equipment.length > 0 && (
            <div className="mt-6">
              <h2
                className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4"
                id="equipment-heading"
              >
                Equipment
              </h2>
              <ul
                aria-labelledby="equipment-heading"
                className="space-y-2"
              >
                {recipe.equipment.map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-slate-600">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-300 flex-shrink-0" aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {/* Right: steps */}
        <section aria-labelledby="steps-heading">
          <h2
            id="steps-heading"
            className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4"
          >
            Instructions
          </h2>
          <RecipeSteps steps={recipe.steps} />
        </section>
      </div>

      {/* Source video */}
      {videoId && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Source Video
            </h2>
            <a
              href={recipe.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-amber-600 font-semibold hover:text-amber-700 transition-colors"
            >
              Watch on YouTube
              <ExternalLink size={12} />
            </a>
          </div>
          <VideoPlayer videoId={videoId} title={recipe.title} />
        </section>
      )}
    </PageContainer>
  )
}

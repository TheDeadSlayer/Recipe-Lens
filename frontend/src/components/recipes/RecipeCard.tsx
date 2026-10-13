import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import type { Recipe } from '../../types/api'
import { extractVideoId, thumbnailUrl } from '../../utils/youtube'

interface Props {
  recipe: Recipe
}

function RecipeThumbnail({ recipe }: { recipe: Recipe }) {
  const videoId = extractVideoId(recipe.source_url)

  if (!videoId) {
    return (
      <div className="w-full aspect-video bg-slate-100 rounded-lg flex items-center justify-center">
        <span className="text-slate-400 text-xs">No preview</span>
      </div>
    )
  }

  return (
    <img
      src={thumbnailUrl(videoId)}
      alt=""
      className="w-full aspect-video object-cover rounded-lg"
      onError={(e) => {
        const target = e.currentTarget
        target.style.display = 'none'
        const placeholder = target.nextElementSibling as HTMLElement | null
        if (placeholder) placeholder.style.display = 'flex'
      }}
    />
  )
}

export default function RecipeCard({ recipe }: Props) {
  const hasNutrition =
    recipe.calories !== null ||
    recipe.protein_g !== null ||
    recipe.carbs_g !== null ||
    recipe.fat_g !== null

  return (
    <article className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col">
      {/* Thumbnail */}
      <div className="relative overflow-hidden bg-slate-100">
        <RecipeThumbnail recipe={recipe} />
        <div
          className="w-full aspect-video bg-slate-100 rounded-lg items-center justify-center hidden"
          aria-hidden="true"
        >
          <span className="text-slate-400 text-xs">No preview</span>
        </div>
      </div>

      {/* Content */}
      <div className="p-5 flex flex-col flex-1">
        <h2 className="font-semibold text-slate-900 text-base leading-snug mb-1 line-clamp-2">
          {recipe.title}
        </h2>
        {recipe.description && (
          <p className="text-sm text-slate-500 leading-relaxed mb-3 line-clamp-2">
            {recipe.description}
          </p>
        )}

        {/* Compact nutrition */}
        {hasNutrition && (
          <div className="flex flex-wrap gap-3 mt-auto mb-4">
            {recipe.calories !== null && (
              <span className="text-xs text-amber-700 bg-amber-50 border border-amber-100 px-2 py-1 rounded-md font-medium">
                {recipe.calories} kcal
              </span>
            )}
            {recipe.protein_g !== null && (
              <span className="text-xs text-slate-600 bg-slate-50 border border-slate-100 px-2 py-1 rounded-md">
                P {recipe.protein_g}g
              </span>
            )}
            {recipe.carbs_g !== null && (
              <span className="text-xs text-slate-600 bg-slate-50 border border-slate-100 px-2 py-1 rounded-md">
                C {recipe.carbs_g}g
              </span>
            )}
            {recipe.fat_g !== null && (
              <span className="text-xs text-slate-600 bg-slate-50 border border-slate-100 px-2 py-1 rounded-md">
                F {recipe.fat_g}g
              </span>
            )}
          </div>
        )}

        <Link
          to={`/recipes/${recipe.id}`}
          className="mt-auto flex items-center gap-1.5 text-sm font-semibold text-amber-600 hover:text-amber-700 transition-colors focus:outline-none focus:underline"
        >
          View recipe
          <ArrowRight size={14} />
        </Link>
      </div>
    </article>
  )
}

import { Link } from 'react-router-dom'
import { ArrowRight, ExternalLink } from 'lucide-react'
import type { Recipe } from '../../types/api'
import IngredientList from '../recipes/IngredientList'
import RecipeSteps from '../recipes/RecipeSteps'
import NutritionSummary from '../recipes/NutritionSummary'

interface Props {
  recipe: Recipe
  onReset: () => void
}

export default function AnalysisResult({ recipe, onReset }: Props) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-auto max-h-[70vh] lg:max-h-none">
      {/* Header */}
      <div className="p-6 border-b border-slate-100">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 leading-snug">
              {recipe.title}
            </h2>
            {recipe.description && (
              <p className="mt-1 text-sm text-slate-500 leading-relaxed">
                {recipe.description}
              </p>
            )}
          </div>
          <Link
            to={`/recipes/${recipe.id}`}
            className="flex-shrink-0 flex items-center gap-1.5 text-xs font-semibold text-amber-600 hover:text-amber-700 transition-colors"
            aria-label="Open full recipe page"
          >
            Full recipe
            <ArrowRight size={14} />
          </Link>
        </div>
      </div>

      {/* Nutrition */}
      <div className="px-6 pt-5">
        <NutritionSummary recipe={recipe} />
      </div>

      {/* Two-column: ingredients + steps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-0 divide-y md:divide-y-0 md:divide-x divide-slate-100 p-6 pt-5">
        {/* Ingredients */}
        <div className="pb-5 md:pb-0 md:pr-6">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-3">
            Ingredients
          </h3>
          <IngredientList ingredients={recipe.ingredients} />

          {recipe.equipment.length > 0 && (
            <div className="mt-5">
              <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-3">
                Equipment
              </h3>
              <ul className="space-y-1.5">
                {recipe.equipment.map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-slate-600">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-300 flex-shrink-0" aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Steps */}
        <div className="pt-5 md:pt-0 md:pl-6">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-3">
            Instructions
          </h3>
          <RecipeSteps steps={recipe.steps} />
        </div>
      </div>

      {/* Footer actions */}
      <div className="px-6 pb-6 flex flex-wrap gap-3">
        <Link
          to={`/recipes/${recipe.id}`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 text-white text-sm font-semibold hover:bg-amber-600 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2"
        >
          View full recipe
          <ExternalLink size={14} />
        </Link>
        <button
          onClick={onReset}
          className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 text-sm font-medium hover:bg-slate-50 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-300 focus:ring-offset-2"
        >
          Analyze another video
        </button>
      </div>
    </div>
  )
}

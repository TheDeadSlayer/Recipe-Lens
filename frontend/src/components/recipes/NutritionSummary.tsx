import type { Recipe } from '../../types/api'

type NutritionField = {
  label: string
  value: number | null
  unit: string
}

function getNutritionFields(recipe: Recipe): NutritionField[] {
  return [
    { label: 'Calories', value: recipe.calories, unit: 'kcal' },
    { label: 'Protein', value: recipe.protein_g, unit: 'g' },
    { label: 'Carbs', value: recipe.carbs_g, unit: 'g' },
    { label: 'Fat', value: recipe.fat_g, unit: 'g' },
  ]
}

interface Props {
  recipe: Recipe
}

export default function NutritionSummary({ recipe }: Props) {
  const fields = getNutritionFields(recipe).filter((f) => f.value !== null)

  if (fields.length === 0) return null

  return (
    <div
      className="grid grid-cols-2 sm:grid-cols-4 gap-3"
      aria-label="Nutrition information"
    >
      {fields.map(({ label, value, unit }) => (
        <div
          key={label}
          className="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 text-center"
        >
          <div className="text-xl font-bold text-amber-700 leading-none">
            {value}
            {unit !== 'kcal' && (
              <span className="text-sm font-medium ml-0.5">{unit}</span>
            )}
          </div>
          <div className="text-xs text-amber-600 mt-1 font-medium uppercase tracking-wide">
            {label}
          </div>
        </div>
      ))}
    </div>
  )
}

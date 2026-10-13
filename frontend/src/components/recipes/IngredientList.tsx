import type { Ingredient } from '../../types/api'

interface Props {
  ingredients: Ingredient[]
}

export default function IngredientList({ ingredients }: Props) {
  if (ingredients.length === 0) {
    return <p className="text-sm text-slate-400 italic">No ingredients listed.</p>
  }

  return (
    <ul className="space-y-2" aria-label="Ingredients">
      {ingredients.map((ing, i) => (
        <li key={i} className="flex items-start gap-3 text-sm">
          <span className="mt-1 w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" aria-hidden="true" />
          <span>
            <span className="font-medium text-slate-800">{ing.name}</span>
            {ing.quantity && (
              <span className="text-slate-500"> — {ing.quantity}</span>
            )}
          </span>
        </li>
      ))}
    </ul>
  )
}

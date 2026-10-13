interface Props {
  steps: string[]
}

export default function RecipeSteps({ steps }: Props) {
  if (steps.length === 0) {
    return <p className="text-sm text-slate-400 italic">No steps listed.</p>
  }

  return (
    <ol className="space-y-4" aria-label="Preparation steps">
      {steps.map((step, i) => (
        <li key={i} className="flex items-start gap-4">
          <span
            className="flex-shrink-0 w-7 h-7 rounded-full bg-amber-500 text-white text-xs font-bold flex items-center justify-center mt-0.5"
            aria-hidden="true"
          >
            {i + 1}
          </span>
          <p className="text-sm text-slate-700 leading-relaxed pt-1">{step}</p>
        </li>
      ))}
    </ol>
  )
}

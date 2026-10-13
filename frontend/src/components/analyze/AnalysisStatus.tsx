import { Loader2, AlertCircle, Ban } from 'lucide-react'
import type { Job } from '../../types/api'

interface Props {
  job: Job
  onReset: () => void
}

export default function AnalysisStatus({ job, onReset }: Props) {
  if (job.status === 'pending' || job.status === 'processing') {
    return (
      <div className="flex flex-col items-center justify-center text-center h-full py-12 px-6">
        <div className="relative mb-6">
          <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center">
            <Loader2
              size={32}
              className="text-amber-500 animate-spin"
              aria-hidden="true"
            />
          </div>
        </div>
        <h2 className="text-xl font-semibold text-slate-900 mb-2">
          Analyzing your video
        </h2>
        <p className="text-sm text-slate-500 max-w-xs leading-relaxed">
          RecipeLens is watching the video and extracting the recipe
          information. This can take a moment for longer videos.
        </p>
        <div className="mt-6 flex gap-1.5" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-2 h-2 rounded-full bg-amber-400 animate-pulse-slow"
              style={{ animationDelay: `${i * 0.3}s` }}
            />
          ))}
        </div>
      </div>
    )
  }

  if (job.status === 'not_recipe') {
    return (
      <div className="flex flex-col items-center justify-center text-center h-full py-12 px-6">
        <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center mb-6">
          <Ban size={28} className="text-amber-500" aria-hidden="true" />
        </div>
        <h2 className="text-xl font-semibold text-slate-900 mb-2">
          No recipe detected
        </h2>
        <p className="text-sm text-slate-500 max-w-xs leading-relaxed mb-3">
          This video doesn't appear to demonstrate or explain a recipe.
        </p>
        {job.classification_reason && (
          <p className="text-sm text-slate-400 italic max-w-xs leading-relaxed mb-6">
            "{job.classification_reason}"
          </p>
        )}
        <button
          onClick={onReset}
          className="mt-2 px-5 py-2.5 rounded-xl bg-amber-500 text-white text-sm font-semibold hover:bg-amber-600 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2"
        >
          Analyze another video
        </button>
      </div>
    )
  }

  if (job.status === 'failed') {
    return (
      <div className="flex flex-col items-center justify-center text-center h-full py-12 px-6">
        <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mb-6">
          <AlertCircle size={28} className="text-red-500" aria-hidden="true" />
        </div>
        <h2 className="text-xl font-semibold text-slate-900 mb-2">
          We couldn't analyze this video
        </h2>
        <p className="text-sm text-slate-500 max-w-xs leading-relaxed mb-6">
          Please try again in a moment or use a different video.
        </p>
        <button
          onClick={onReset}
          className="px-5 py-2.5 rounded-xl bg-slate-900 text-white text-sm font-semibold hover:bg-slate-700 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2"
        >
          Try again
        </button>
      </div>
    )
  }

  return null
}

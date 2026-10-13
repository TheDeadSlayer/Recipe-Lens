import { useState, useRef } from 'react'
import { Search } from 'lucide-react'
import { isValidYouTubeUrl } from '../../utils/youtube'

interface Props {
  onSubmit: (url: string) => void
  isLoading: boolean
}

export default function VideoUrlForm({ onSubmit, isLoading }: Props) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const trimmed = value.trim()
  const isValid = isValidYouTubeUrl(trimmed)
  const canSubmit = isValid && !isLoading

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    onSubmit(trimmed)
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <label htmlFor="video-url" className="sr-only">
        YouTube video URL
      </label>
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-slate-400">
            <Search size={18} />
          </div>
          <input
            id="video-url"
            ref={inputRef}
            type="url"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Paste a YouTube URL here…"
            disabled={isLoading}
            autoFocus
            className={[
              'w-full pl-11 pr-4 py-3.5 rounded-xl border text-sm transition-colors outline-none',
              'placeholder:text-slate-400 bg-white',
              'focus:ring-2 focus:ring-amber-400 focus:border-amber-400',
              trimmed && !isValid
                ? 'border-red-300 text-red-800'
                : 'border-slate-300 text-slate-900',
              isLoading ? 'opacity-60 cursor-not-allowed' : '',
            ].join(' ')}
            aria-invalid={trimmed !== '' && !isValid}
            aria-describedby={trimmed && !isValid ? 'url-error' : undefined}
          />
        </div>
        <button
          type="submit"
          disabled={!canSubmit}
          className={[
            'px-6 py-3.5 rounded-xl text-sm font-semibold transition-all',
            'focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2',
            canSubmit
              ? 'bg-amber-500 text-white hover:bg-amber-600 active:scale-95 shadow-sm'
              : 'bg-slate-200 text-slate-400 cursor-not-allowed',
          ].join(' ')}
        >
          {isLoading ? 'Analyzing…' : 'Analyze Recipe'}
        </button>
      </div>
      {trimmed && !isValid && (
        <p id="url-error" className="mt-2 text-xs text-red-600" role="alert">
          Please enter a valid YouTube URL (youtube.com or youtu.be).
        </p>
      )}
    </form>
  )
}

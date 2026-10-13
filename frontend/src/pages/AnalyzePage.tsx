import { useState, useEffect, useRef, useCallback } from 'react'
import { Sparkles } from 'lucide-react'
import PageContainer from '../components/layout/PageContainer'
import VideoUrlForm from '../components/analyze/VideoUrlForm'
import VideoPlayer from '../components/analyze/VideoPlayer'
import AnalysisStatus from '../components/analyze/AnalysisStatus'
import AnalysisResult from '../components/analyze/AnalysisResult'
import { createJob, getJob } from '../api/jobs'
import { getRecipe } from '../api/recipes'
import { extractVideoId } from '../utils/youtube'
import type { Job, Recipe } from '../types/api'

type Phase =
  | { kind: 'idle' }
  | { kind: 'submitting' }
  | { kind: 'polling'; job: Job; videoId: string }
  | { kind: 'done'; job: Job; recipe: Recipe; videoId: string }
  | { kind: 'terminal'; job: Job; videoId: string } // not_recipe or failed
  | { kind: 'already_exists'; recipe: Recipe; videoId: string }

const POLL_INTERVAL_MS = 2000
const TERMINAL_STATUSES = new Set(['completed', 'not_recipe', 'failed'])

export default function AnalyzePage() {
  const [phase, setPhase] = useState<Phase>({ kind: 'idle' })
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (pollingRef.current !== null) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }, [])

  // Clean up polling on unmount
  useEffect(() => () => stopPolling(), [stopPolling])

  const handleSubmit = useCallback(
    async (url: string) => {
      const videoId = extractVideoId(url)
      if (!videoId) return

      setPhase({ kind: 'submitting' })
      stopPolling()

      try {
        const response = await createJob(url)

        // ── Layer 1 dedup: server found an existing recipe for this video ────
        if (response.already_exists && response.recipe) {
          setPhase({ kind: 'already_exists', recipe: response.recipe, videoId })
          return
        }

        // ── New job: start polling ────────────────────────────────────────────
        if (!response.job_id) {
          // Unexpected state — fall back to idle
          setPhase({ kind: 'idle' })
          return
        }

        const jobId = response.job_id
        // Seed polling phase immediately with a synthetic pending job so the
        // UI shows the spinner without waiting for the first poll to return.
        const syntheticJob: Job = {
          id: jobId,
          source_url: url,
          status: 'pending',
          recipe_id: null,
          error_message: null,
          classification_reason: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
        setPhase({ kind: 'polling', job: syntheticJob, videoId })

        pollingRef.current = setInterval(async () => {
          try {
            const updated = await getJob(jobId)

            if (TERMINAL_STATUSES.has(updated.status)) {
              stopPolling()

              if (updated.status === 'completed' && updated.recipe_id) {
                try {
                  const recipe = await getRecipe(updated.recipe_id)
                  setPhase({ kind: 'done', job: updated, recipe, videoId })
                } catch {
                  setPhase({ kind: 'terminal', job: updated, videoId })
                }
              } else {
                setPhase({ kind: 'terminal', job: updated, videoId })
              }
            } else {
              setPhase((prev) =>
                prev.kind === 'polling' ? { ...prev, job: updated } : prev,
              )
            }
          } catch {
            // Transient fetch error — keep polling
          }
        }, POLL_INTERVAL_MS)
      } catch {
        setPhase({ kind: 'idle' })
      }
    },
    [stopPolling],
  )

  const handleReset = useCallback(() => {
    stopPolling()
    setPhase({ kind: 'idle' })
  }, [stopPolling])

  const isLoading =
    phase.kind === 'submitting' || phase.kind === 'polling'

  // ── Hero (idle) ────────────────────────────────────────────────────────────
  if (phase.kind === 'idle') {
    return (
      <PageContainer>
        <div className="max-w-2xl mx-auto pt-12 pb-16 text-center">
          <div className="inline-flex items-center gap-2 bg-amber-50 border border-amber-100 rounded-full px-4 py-1.5 text-amber-700 text-xs font-semibold mb-8 tracking-wide uppercase">
            <Sparkles size={13} />
            Powered by Gemini
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
            Turn cooking videos<br />
            <span className="text-amber-500">into structured recipes.</span>
          </h1>
          <p className="text-lg text-slate-500 leading-relaxed mb-10 max-w-lg mx-auto">
            Paste a YouTube video and let AI identify the recipe, ingredients,
            instructions, and nutrition information.
          </p>
          <VideoUrlForm onSubmit={handleSubmit} isLoading={false} />
          <p className="mt-4 text-xs text-slate-400">
            Supports youtube.com/watch, youtu.be, and YouTube Shorts
          </p>
        </div>
      </PageContainer>
    )
  }

  // ── Submitting (brief flash) ────────────────────────────────────────────────
  if (phase.kind === 'submitting') {
    return (
      <PageContainer>
        <div className="max-w-2xl mx-auto pt-8 pb-4">
          <VideoUrlForm onSubmit={handleSubmit} isLoading={true} />
        </div>
      </PageContainer>
    )
  }

  // ── Two-column analysis layout ─────────────────────────────────────────────
  const videoId =
    phase.kind === 'polling' ||
    phase.kind === 'done' ||
    phase.kind === 'terminal' ||
    phase.kind === 'already_exists'
      ? phase.videoId
      : ''

  const rightPanel = () => {
    if (phase.kind === 'done') {
      return (
        <AnalysisResult recipe={phase.recipe} onReset={handleReset} />
      )
    }
    if (phase.kind === 'already_exists') {
      return (
        <div className="flex flex-col gap-4">
          {/* Already-exists informational banner */}
          <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
            <p className="font-semibold mb-0.5">Already in your recipes</p>
            <p className="text-sky-700">
              You've analyzed this video before, so we loaded the saved recipe instead.{' '}
              <a
                href={`/recipes/${phase.recipe.id}`}
                className="underline font-medium hover:text-sky-900"
              >
                View recipe →
              </a>
            </p>
          </div>
          <AnalysisResult recipe={phase.recipe} onReset={handleReset} />
        </div>
      )
    }
    if (phase.kind === 'polling' || phase.kind === 'terminal') {
      return (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm h-full min-h-64">
          <AnalysisStatus job={phase.job} onReset={handleReset} />
        </div>
      )
    }
    return null
  }

  return (
    <PageContainer className="py-6">
      {/* URL form above the two-column layout */}
      <div className="mb-6">
        <VideoUrlForm onSubmit={handleSubmit} isLoading={isLoading} />
      </div>

      {/* Two-column layout: video | status/result */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <div>
          <VideoPlayer videoId={videoId} />
        </div>
        <div>{rightPanel()}</div>
      </div>
    </PageContainer>
  )
}

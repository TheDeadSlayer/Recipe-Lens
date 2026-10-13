import { apiFetch } from './client'
import type { Job, JobCreateResponse } from '../types/api'

export function createJob(sourceUrl: string): Promise<JobCreateResponse> {
  return apiFetch<JobCreateResponse>('/api/v1/jobs', {
    method: 'POST',
    body: JSON.stringify({ source_url: sourceUrl }),
  })
}

export function getJob(jobId: string): Promise<Job> {
  return apiFetch<Job>(`/api/v1/jobs/${jobId}`)
}

// Centralized API base URL.
// Reads VITE_API_BASE_URL from the environment (set at build/dev time).
// Falls back to http://localhost:8000 for local development without a .env.
// In production with same-origin Nginx proxy, set VITE_API_BASE_URL="" so
// requests go to /api/v1/... relative to the page origin.
const API_BASE = (import.meta.env['VITE_API_BASE_URL'] as string | undefined) ?? 'http://localhost:8000'

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`
  const response = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // ignore parse failure — use status code message
    }
    throw new ApiError(response.status, message)
  }

  return response.json() as Promise<T>
}

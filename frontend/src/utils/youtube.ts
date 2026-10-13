/**
 * YouTube URL utilities.
 *
 * Handles all common YouTube URL formats:
 *   https://www.youtube.com/watch?v=VIDEO_ID
 *   https://youtu.be/VIDEO_ID
 *   https://www.youtube.com/shorts/VIDEO_ID
 *   http variants and URLs without www
 */

/**
 * Extract the YouTube video ID from a URL.
 * Returns null if the URL is not a recognised YouTube format.
 */
export function extractVideoId(url: string): string | null {
  try {
    const parsed = new URL(url.trim())
    const host = parsed.hostname.replace(/^www\./, '')

    // youtu.be/VIDEO_ID
    if (host === 'youtu.be') {
      const id = parsed.pathname.slice(1).split('/')[0]
      return id ? id : null
    }

    if (host === 'youtube.com' || host === 'm.youtube.com') {
      // /shorts/VIDEO_ID
      const shortsMatch = parsed.pathname.match(/^\/shorts\/([^/?#]+)/)
      if (shortsMatch?.[1]) return shortsMatch[1]

      // /watch?v=VIDEO_ID
      const v = parsed.searchParams.get('v')
      if (v) return v

      // /embed/VIDEO_ID
      const embedMatch = parsed.pathname.match(/^\/embed\/([^/?#]+)/)
      if (embedMatch?.[1]) return embedMatch[1]
    }

    return null
  } catch {
    return null
  }
}

/**
 * Returns true if the URL is a supported YouTube video URL.
 */
export function isValidYouTubeUrl(url: string): boolean {
  return extractVideoId(url) !== null
}

/**
 * Build a YouTube embed URL from a video ID.
 */
export function embedUrl(videoId: string): string {
  return `https://www.youtube.com/embed/${videoId}`
}

/**
 * Build a YouTube thumbnail URL from a video ID.
 * Uses hqdefault (480×360) — available for all videos, no API key needed.
 */
export function thumbnailUrl(videoId: string): string {
  return `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`
}

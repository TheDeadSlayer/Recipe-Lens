import { describe, it, expect } from 'vitest'
import {
  extractVideoId,
  isValidYouTubeUrl,
  embedUrl,
  thumbnailUrl,
} from '../utils/youtube'

describe('extractVideoId', () => {
  it('parses youtube.com/watch?v=', () => {
    expect(extractVideoId('https://www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ')
  })

  it('parses youtu.be/', () => {
    expect(extractVideoId('https://youtu.be/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ')
  })

  it('parses youtube.com/shorts/', () => {
    expect(extractVideoId('https://www.youtube.com/shorts/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ')
  })

  it('parses URL without www', () => {
    expect(extractVideoId('https://youtube.com/watch?v=dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ')
  })

  it('parses http variant', () => {
    expect(extractVideoId('http://www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ')
  })

  it('handles extra query params', () => {
    expect(extractVideoId('https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s')).toBe('dQw4w9WgXcQ')
  })

  it('returns null for non-YouTube URL', () => {
    expect(extractVideoId('https://vimeo.com/123456789')).toBeNull()
  })

  it('returns null for plain text', () => {
    expect(extractVideoId('not a url at all')).toBeNull()
  })

  it('returns null for empty string', () => {
    expect(extractVideoId('')).toBeNull()
  })

  it('returns null for a YouTube homepage without video', () => {
    expect(extractVideoId('https://www.youtube.com/')).toBeNull()
  })
})

describe('isValidYouTubeUrl', () => {
  it('returns true for valid youtube.com/watch URL', () => {
    expect(isValidYouTubeUrl('https://www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe(true)
  })

  it('returns true for youtu.be short URL', () => {
    expect(isValidYouTubeUrl('https://youtu.be/dQw4w9WgXcQ')).toBe(true)
  })

  it('returns true for YouTube Short', () => {
    expect(isValidYouTubeUrl('https://www.youtube.com/shorts/dQw4w9WgXcQ')).toBe(true)
  })

  it('returns false for a non-YouTube URL', () => {
    expect(isValidYouTubeUrl('https://example.com/video')).toBe(false)
  })

  it('returns false for empty string', () => {
    expect(isValidYouTubeUrl('')).toBe(false)
  })
})

describe('embedUrl', () => {
  it('returns the correct embed URL', () => {
    expect(embedUrl('dQw4w9WgXcQ')).toBe('https://www.youtube.com/embed/dQw4w9WgXcQ')
  })
})

describe('thumbnailUrl', () => {
  it('returns the hqdefault thumbnail URL', () => {
    expect(thumbnailUrl('dQw4w9WgXcQ')).toBe(
      'https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg',
    )
  })
})

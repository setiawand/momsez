export function apiBase() {
  return process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'
}

export function authHeaders() {
  const t = (typeof window !== 'undefined') ? localStorage.getItem('MOMSEZ_JWT') : null
  return t ? { Authorization: `Bearer ${t}` } : {}
}

export function wsUrl(path: string) {
  const base = apiBase()
  const u = new URL(path, base)
  u.protocol = u.protocol.replace('http', 'ws')
  return u.toString()
}

// Build a safe download URL for a transcript/audio path returned by the API.
// Normalizes absolute container paths like "/app/output/..." to relative "output/..."
export function transcriptDownloadUrl(filePath?: string | null) {
  if (!filePath) return '#'
  const p = String(filePath)
  const idx = p.indexOf('/output/')
  let rel = p
  if (idx >= 0) {
    rel = p.slice(idx + 1) // drop the leading slash -> output/...
  } else if (p.startsWith('output/')) {
    rel = p
  } else {
    // best-effort: strip all leading slashes
    rel = p.replace(/^\/+/, '')
  }
  return `${apiBase().replace(/\/$/, '')}/transcription/download/${rel}`
}

// Build a content URL (JSON response with transcript text)
export function transcriptContentUrl(filePath?: string | null) {
  if (!filePath) return '#'
  const p = String(filePath)
  const idx = p.indexOf('/output/')
  let rel = p
  if (idx >= 0) {
    rel = p.slice(idx + 1)
  } else if (p.startsWith('output/')) {
    rel = p
  } else {
    rel = p.replace(/^\/+/, '')
  }
  return `${apiBase().replace(/\/$/, '')}/transcription/content/${rel}`
}

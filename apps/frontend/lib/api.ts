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


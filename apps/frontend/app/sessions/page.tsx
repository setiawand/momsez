"use client"
import useSWR from 'swr'
import Link from 'next/link'
import { apiBase, authHeaders } from '../../lib/api'

const fetcher = (url: string) => fetch(url, { headers: authHeaders() }).then(r => r.json())

export default function SessionsPage() {
  const { data, error, isLoading, mutate } = useSWR(`${apiBase()}/sessions`, fetcher)

  return (
    <main style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h1>My Sessions</h1>
      <div style={{ margin: '12px 0' }}>
        <Link href="/sessions/start">Start a session</Link>
      </div>
      {isLoading && <div>Loading...</div>}
      {error && <div style={{ color: 'crimson' }}>Error loading sessions</div>}
      <ul style={{ display: 'grid', gap: 8 }}>
        {(data || []).map((s: any) => (
          <li key={s.session_id} style={{ border: '1px solid #ddd', padding: 12 }}>
            <div><b>{s.session_id}</b></div>
            <div>Status: {s.status}</div>
            <div>Start: {s.start_time}</div>
            <div><Link href={`/sessions/${s.session_id}`}>Open</Link></div>
          </li>
        ))}
      </ul>
    </main>
  )
}


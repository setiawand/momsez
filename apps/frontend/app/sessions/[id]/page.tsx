"use client"
import useSWR from 'swr'
import { useEffect, useState } from 'react'
import { apiBase, authHeaders, wsUrl } from '../../../lib/api'
import { useParams } from 'next/navigation'

const fetcher = (url: string) => fetch(url, { headers: authHeaders() }).then(r => r.json())

export default function SessionDetail() {
  const params = useParams<{ id: string }>()
  const id = params.id
  const { data, mutate } = useSWR(`${apiBase()}/sessions/${id}/status`, fetcher)
  const [events, setEvents] = useState<string[]>([])

  useEffect(() => {
    const token = localStorage.getItem('MOMSEZ_JWT') || ''
    const u = wsUrl(`/ws/session?session_id=${id}&token=${encodeURIComponent(token)}`)
    const ws = new WebSocket(u)
    ws.onmessage = (ev) => {
      setEvents(prev => [ev.data, ...prev].slice(0, 50))
      mutate()
    }
    return () => ws.close()
  }, [id, mutate])

  const stop = async () => {
    await fetch(`${apiBase()}/sessions/${id}/stop`, { method: 'POST', headers: authHeaders() })
    mutate()
  }

  const cancel = async () => {
    await fetch(`${apiBase()}/sessions/${id}/cancel`, { method: 'POST', headers: authHeaders() })
    mutate()
  }

  return (
    <main style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h1>Session {id}</h1>
      <div>Status: {data?.status}</div>
      <div style={{ display: 'flex', gap: 8, margin: '12px 0' }}>
        <button onClick={stop}>Stop</button>
        <button onClick={cancel}>Cancel</button>
      </div>
      {data?.transcript_path && (
        <div>
          <a href={`${apiBase().replace(/\/$/, '')}/${data.transcript_path}`} target="_blank">Download transcript</a>
        </div>
      )}
      <h3>Events</h3>
      <pre style={{ background: '#fafafa', padding: 12, maxHeight: 240, overflow: 'auto' }}>{events.join('\n')}</pre>
    </main>
  )
}


"use client"
import useSWR from 'swr'
import Link from 'next/link'
import { useMemo, useState } from 'react'
import { apiBase, authHeaders } from '../lib/api'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'

const fetcher = (url: string) => fetch(url, { headers: authHeaders() }).then(r => r.json())

export default function Home() {
  const { data: sessions, isLoading, error, mutate } = useSWR(`${apiBase()}/sessions`, fetcher, { refreshInterval: 4000 })
  const { data: health } = useSWR(`${apiBase()}/health`, (u)=>fetch(u).then(r=>r.json()), { refreshInterval: 15000 })
  const token = typeof window !== 'undefined' ? localStorage.getItem('MOMSEZ_JWT') : null
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const filtered = useMemo(() => {
    const list = Array.isArray(sessions) ? sessions : []
    if (statusFilter === 'all') return list
    return list.filter((s: any) => s.status === statusFilter)
  }, [sessions, statusFilter])

  return (
    <main className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <div className="text-sm text-muted-foreground">Monitor sessions, start new captures, and view transcripts</div>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/sessions/start"><Button>Start Session</Button></Link>
          <Link href="/ingest"><Button variant="secondary">Open Ingest</Button></Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="py-4">
            <div className="text-sm text-muted-foreground">Auth</div>
            <div className="text-lg font-medium mt-1">{token ? 'Signed In' : 'Not Signed In'}</div>
            <div className="mt-3"><Link href="/login"><Button size="sm" variant="ghost">{token ? 'Refresh Token' : 'Login'}</Button></Link></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="text-sm text-muted-foreground">Server Health</div>
            <div className="text-lg font-medium mt-1">{health?.status || 'unknown'}</div>
            <div className="text-xs text-muted-foreground mt-1">{health?.timestamp || ''}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="text-sm text-muted-foreground">Counts</div>
            <div className="text-lg font-medium mt-1">{Array.isArray(sessions) ? sessions.length : 0} sessions</div>
            <div className="text-xs text-muted-foreground mt-1">auto-refreshing</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="py-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium">Recent Sessions</h2>
            <div className="flex items-center gap-2 text-sm">
              <label className="text-muted-foreground">Status</label>
              <select className="border rounded px-2 py-1 text-sm" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}>
                <option value="all">All</option>
                <option value="awaiting-chunks">awaiting-chunks</option>
                <option value="ingesting">ingesting</option>
                <option value="processing">processing</option>
                <option value="completed">completed</option>
                <option value="error">error</option>
              </select>
            </div>
          </div>

          {isLoading && <div className="text-sm">Loading sessions…</div>}
          {error && <div className="text-sm text-red-600">Failed to load sessions</div>}

          <div className="grid gap-3">
            {filtered.map((s: any) => (
              <div key={s.session_id} className="border rounded-md p-3 hover:bg-muted/40 transition">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-muted-foreground">{s.session_id}</span>
                      <StatusPill status={s.status} />
                    </div>
                    <div className="text-sm text-muted-foreground truncate">{s.output_dir}</div>
                    {s.start_time && <div className="text-xs text-muted-foreground">Started: {s.start_time}</div>}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {s.transcript_path && (
                      <a className="text-sm underline" href={`${apiBase().replace(/\/$/, '')}/${s.transcript_path}`} target="_blank">Transcript</a>
                    )}
                    <Link href={`/sessions/${s.session_id}`}><Button size="sm" variant="secondary">Open</Button></Link>
                  </div>
                </div>
                {s.error_message && <div className="text-xs text-red-600 mt-1">{s.error_message}</div>}
              </div>
            ))}
            {!isLoading && filtered.length === 0 && (
              <div className="text-sm text-muted-foreground">No sessions</div>
            )}
          </div>
        </CardContent>
      </Card>
    </main>
  )
}

function StatusPill({ status }: { status?: string }) {
  const color = status === 'completed' ? 'bg-green-600' : status === 'processing' ? 'bg-amber-600' : status === 'ingesting' ? 'bg-blue-600' : status === 'error' ? 'bg-red-600' : 'bg-gray-400'
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full text-white ${color}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-white/90" />
      {status || 'unknown'}
    </span>
  )
}

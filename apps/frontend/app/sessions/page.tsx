"use client"
import useSWR from 'swr'
import Link from 'next/link'
import { Button } from '../../components/ui/button'
import { Card, CardContent } from '../../components/ui/card'
import { apiBase, authHeaders } from '../../lib/api'

const fetcher = (url: string) => fetch(url, { headers: authHeaders() }).then(r => r.json())

export default function SessionsPage() {
  const { data, error, isLoading, mutate } = useSWR(`${apiBase()}/sessions`, fetcher, { refreshInterval: 4000 })

  return (
    <main className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">My Sessions</h1>
        <Link href="/sessions/start"><Button>Start a session</Button></Link>
      </div>
      {isLoading && <div>Loading...</div>}
      {error && <div className="text-red-600">Error loading sessions</div>}
      <div className="grid gap-3">
        {(data || []).map((s: any) => (
          <Card key={s.session_id}>
            <CardContent className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <div className="font-mono text-sm truncate">{s.session_id}</div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">{s.status}</span>
                  <Link href={`/sessions/${s.session_id}`}><Button size="sm" variant="secondary">Open</Button></Link>
                </div>
              </div>
              <div className="text-sm text-muted-foreground">Start: {s.start_time || '-'}</div>
              {s.transcript_path && (
                <div className="text-xs"><a className="underline" href={`${apiBase().replace(/\/$/, '')}/${s.transcript_path}`} target="_blank">Transcript</a></div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  )
}

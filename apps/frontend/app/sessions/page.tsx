"use client"
import useSWR from 'swr'
import Link from 'next/link'
import { Button } from '../../components/ui/button'
import { Card, CardContent } from '../../components/ui/card'
import { apiBase, authHeaders } from '../../lib/api'

const fetcher = (url: string) => fetch(url, { headers: authHeaders() }).then(r => r.json())

export default function SessionsPage() {
  const { data, error, isLoading, mutate } = useSWR(`${apiBase()}/sessions`, fetcher)

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
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="font-mono text-sm">{s.session_id}</div>
                <Link href={`/sessions/${s.session_id}`}><Button variant="secondary">Open</Button></Link>
              </div>
              <div className="text-sm text-muted-foreground mt-2">Status: {s.status} • Start: {s.start_time}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  )
}

"use client"
import useSWR from 'swr'
import { useEffect, useState } from 'react'
import { apiBase, authHeaders, wsUrl, transcriptContentUrl } from '../../../lib/api'
import { Button } from '../../../components/ui/button'
import { Card, CardContent } from '../../../components/ui/card'
import { useParams } from 'next/navigation'
import { Modal } from '../../../components/ui/modal'

const fetcher = (url: string) => fetch(url, { headers: authHeaders() }).then(r => r.json())

export default function SessionDetail() {
  const params = useParams<{ id: string }>()
  const id = params.id
  const { data, mutate } = useSWR(`${apiBase()}/sessions/${id}/status`, fetcher)
  const [events, setEvents] = useState<string[]>([])
  const [preview, setPreview] = useState<{open: boolean, title?: string, content?: string, loading?: boolean}>({ open: false })

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
    <main className="space-y-4">
      <h1 className="text-2xl font-semibold">Session {id}</h1>
      <div className="text-sm text-muted-foreground">Status: {data?.status}</div>
      {typeof data?.audio_duration === 'number' && (
        <div className="text-sm text-muted-foreground">Audio duration: {data.audio_duration.toFixed(1)}s</div>
      )}
      <div className="flex gap-2">
        <Button onClick={stop}>Stop</Button>
        <Button variant="ghost" onClick={cancel}>Cancel</Button>
        {data?.transcript_path && (
          <button className="btn btn-secondary" onClick={async ()=>{
            setPreview({ open: true, title: 'Transcript preview', loading: true })
            try {
              const res = await fetch(transcriptContentUrl(data.transcript_path), { headers: authHeaders() })
              const d = await res.json()
              setPreview({ open: true, title: d.filename || 'Transcript', content: d.content, loading: false })
            } catch (e:any) {
              setPreview({ open: true, title: 'Error', content: String(e), loading: false })
            }
          }}>Preview transcript</button>
        )}
      </div>
      <Card>
        <CardContent>
          <h3 className="font-medium mb-2">Events</h3>
          <pre className="bg-muted rounded-md p-3 max-h-60 overflow-auto whitespace-pre-wrap text-sm">{events.join('\n')}</pre>
        </CardContent>
      </Card>

      <Modal open={preview.open} onClose={()=>setPreview({ open: false })} title={preview.title}>
        {preview.loading ? (
          <div className="text-sm text-muted-foreground">Loading…</div>
        ) : (
          <pre className="whitespace-pre-wrap text-sm">{preview.content || ''}</pre>
        )}
      </Modal>
    </main>
  )
}

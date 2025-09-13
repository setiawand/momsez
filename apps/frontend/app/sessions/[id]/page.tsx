"use client"
import useSWR from 'swr'
import { useEffect, useState } from 'react'
import { apiBase, authHeaders, wsUrl, transcriptContentUrl, transcriptDownloadUrl } from '../../../lib/api'
import { Card, CardContent } from '../../../components/ui/card'
import { useParams } from 'next/navigation'

const fetcher = (url: string) => fetch(url, { headers: authHeaders() }).then(r => r.json())

export default function SessionDetail() {
  const params = useParams<{ id: string }>()
  const id = params.id
  const { data, mutate } = useSWR(`${apiBase()}/sessions/${id}/status`, fetcher)
  const transcriptUrl = data?.transcript_path ? transcriptContentUrl(data.transcript_path) : null
  const { data: tdata } = useSWR(transcriptUrl, (u: string) => fetch(u, { headers: authHeaders() }).then(r => r.json()), { revalidateOnFocus: false })
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('MOMSEZ_JWT') || ''
    const u = wsUrl(`/ws/session?session_id=${id}&token=${encodeURIComponent(token)}`)
    const ws = new WebSocket(u)
    ws.onmessage = () => { mutate() }
    return () => ws.close()
  }, [id, mutate])

  return (
    <main className="space-y-4">
      <h1 className="text-2xl font-semibold">Session {id}</h1>
      <div className="text-sm text-muted-foreground">Status: {data?.status}</div>
      {typeof data?.audio_duration === 'number' && (
        <div className="text-sm text-muted-foreground">Audio duration: {data.audio_duration.toFixed(1)}s</div>
      )}
      <Card>
        <CardContent>
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium">Transcript</h3>
            {tdata?.content && (
              <button
                className="text-xs underline"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(tdata.content)
                    setCopied(true)
                    setTimeout(() => setCopied(false), 1500)
                  } catch {
                    setCopied(false)
                  }
                }}
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
            )}
          </div>
          {data?.transcript_path ? (
            tdata?.content ? (
              <>
                <pre className="bg-muted rounded-md p-3 max-h-[60vh] overflow-auto whitespace-pre-wrap text-sm">{tdata.content}</pre>
                <div className="mt-2 text-xs">
                  <a className="underline" href={transcriptDownloadUrl(data.transcript_path)} target="_blank" rel="noreferrer">Download .txt</a>
                </div>
              </>
            ) : (
              <div className="text-sm text-muted-foreground">Loading transcript…</div>
            )
          ) : (
            <div className="text-sm text-muted-foreground">Transcript not available yet</div>
          )}
        </CardContent>
      </Card>
    </main>
  )
}

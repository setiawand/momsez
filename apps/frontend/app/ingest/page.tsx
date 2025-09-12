"use client"
import { useEffect, useRef, useState } from 'react'
import { apiBase, authHeaders } from '../../lib/api'

export default function IngestPage() {
  const [sessionId, setSessionId] = useState<string>('')
  const [status, setStatus] = useState<string>('idle')
  const mediaRecRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<number>(0)
  const [log, setLog] = useState<string[]>([])

  const logLine = (s: string) => setLog(prev => [s, ...prev].slice(0, 100))

  const startSession = async () => {
    const res = await fetch(`${apiBase()}/sessions/start`, {
      method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ ingest: true, language: 'id' })
    })
    if (!res.ok) { logLine('start failed: ' + (await res.text())); return }
    const data = await res.json();
    setSessionId(data.session_id)
    logLine('session started: ' + data.session_id)
  }

  const startRecording = async () => {
    if (!sessionId) { logLine('start a session first'); return }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    streamRef.current = stream
    const mr = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
    chunksRef.current = 0
    mr.ondataavailable = async (ev) => {
      if (!ev.data || ev.data.size === 0) return
      chunksRef.current += 1
      const file = new File([ev.data], `chunk_${String(chunksRef.current).padStart(6, '0')}.webm`, { type: ev.data.type })
      const fd = new FormData(); fd.append('file', file)
      const resp = await fetch(`${apiBase()}/sessions/${sessionId}/ingest`, { method: 'POST', headers: authHeaders(), body: fd })
      if (!resp.ok) {
        logLine('upload failed: ' + (await resp.text()))
      } else {
        logLine('uploaded chunk #' + chunksRef.current)
      }
    }
    mr.start(3000) // 3s chunks
    mediaRecRef.current = mr
    setStatus('recording')
    logLine('recording...')
  }

  const stopRecording = async () => {
    mediaRecRef.current?.stop()
    streamRef.current?.getTracks().forEach(t => t.stop())
    setStatus('stopped')
    logLine('stopped, finishing...')
    const resp = await fetch(`${apiBase()}/sessions/${sessionId}/finish`, { method: 'POST', headers: authHeaders() })
    if (!resp.ok) { logLine('finish failed: ' + (await resp.text())); return }
    const data = await resp.json()
    logLine('completed: ' + (data.transcript_path || ''))
  }

  useEffect(() => () => {
    mediaRecRef.current?.stop()
    streamRef.current?.getTracks().forEach(t => t.stop())
  }, [])

  return (
    <main style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h1>Browser Ingest Demo</h1>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button onClick={startSession} disabled={!!sessionId}>Start Ingest Session</button>
        <button onClick={startRecording} disabled={!sessionId || status === 'recording'}>Start Recording</button>
        <button onClick={stopRecording} disabled={status !== 'recording'}>Stop + Finish</button>
      </div>
      <div>Session: {sessionId || '-'}</div>
      <h3>Log</h3>
      <pre style={{ background: '#fafafa', padding: 12, maxHeight: 240, overflow: 'auto' }}>{log.join('\n')}</pre>
    </main>
  )
}


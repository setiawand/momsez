"use client"
import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiBase, authHeaders } from '../../lib/api'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader } from '../../components/ui/card'

export default function IngestPage() {
  const [sessionId, setSessionId] = useState<string>('')
  const [status, setStatus] = useState<string>('idle')
  const mediaRecRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<number>(0)
  const sessionIdRef = useRef<string>('')
  const [log, setLog] = useState<string[]>([])
  const [elapsed, setElapsed] = useState<number>(0)
  const [level, setLevel] = useState<number>(0)
  const timerRef = useRef<any>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const router = useRouter()

  const logLine = (s: string) => setLog(prev => [s, ...prev].slice(0, 100))

  const startRecording = async () => {
    // Create session automatically if needed
    if (!sessionId) {
      const res = await fetch(`${apiBase()}/sessions/start`, {
        method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ ingest: true, language: 'id' })
      })
      if (!res.ok) { logLine('start failed: ' + (await res.text())); return }
      const data = await res.json();
      setSessionId(data.session_id)
      sessionIdRef.current = data.session_id
      logLine('session started: ' + data.session_id)
    } else {
      sessionIdRef.current = sessionId
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    streamRef.current = stream
    // Setup audio level metering
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
      const src = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 2048
      src.connect(analyser)
      audioCtxRef.current = ctx
      analyserRef.current = analyser
      const buf = new Uint8Array(analyser.frequencyBinCount)
      const loop = () => {
        if (!analyserRef.current) return
        analyserRef.current.getByteTimeDomainData(buf)
        // Compute normalized RMS 0..1
        let sum = 0
        for (let i = 0; i < buf.length; i++) {
          const v = (buf[i] - 128) / 128
          sum += v * v
        }
        const rms = Math.sqrt(sum / buf.length)
        setLevel(Math.min(1, rms * 2))
        requestAnimationFrame(loop)
      }
      requestAnimationFrame(loop)
    } catch {}
    const mr = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
    chunksRef.current = 0
    mr.ondataavailable = async (ev) => {
      if (!ev.data || ev.data.size === 0) return
      chunksRef.current += 1
      const file = new File([ev.data], `chunk_${String(chunksRef.current).padStart(6, '0')}.webm`, { type: ev.data.type })
      const fd = new FormData(); fd.append('file', file)
      const sid = sessionIdRef.current
      if (!sid) { logLine('upload skipped: no session id yet'); return }
      const resp = await fetch(`${apiBase()}/sessions/${sid}/ingest`, { method: 'POST', headers: authHeaders(), body: fd })
      if (!resp.ok) {
        logLine('upload failed: ' + (await resp.text()))
      } else {
        logLine('uploaded chunk #' + chunksRef.current)
      }
    }
    mr.onstop = async () => {
      // call finish only after recorder is fully stopped and last chunk delivered
      const sid = sessionIdRef.current
      const resp = await fetch(`${apiBase()}/sessions/${sid}/finish`, { method: 'POST', headers: authHeaders() })
      if (!resp.ok) { logLine('finish failed: ' + (await resp.text())); return }
      const data = await resp.json()
      logLine('completed: ' + (data.transcript_path || ''))
      try { router.push(`/sessions/${sid}`) } catch {}
    }
    mr.start(3000) // 3s chunks
    mediaRecRef.current = mr
    setStatus('recording')
    logLine('recording...')
    const t0 = Date.now()
    timerRef.current = setInterval(() => setElapsed(Math.floor((Date.now() - t0) / 1000)), 500)
  }

  const stopRecording = async () => {
    // Flush any buffered data before stopping
    try { mediaRecRef.current?.requestData() } catch {}
    setTimeout(() => {
      try { mediaRecRef.current?.stop() } catch {}
      try { streamRef.current?.getTracks().forEach(t => t.stop()) } catch {}
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null }
      try { audioCtxRef.current?.close() } catch {}
      analyserRef.current = null
    }, 150)
    setStatus('stopped')
    logLine('stopped, finishing...')
  }

  useEffect(() => () => {
    mediaRecRef.current?.stop()
    streamRef.current?.getTracks().forEach(t => t.stop())
  }, [])

  return (
    <main className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Record in Browser</h1>
        <div className="text-sm text-muted-foreground">Create session, upload chunks, and transcribe</div>
      </div>

      <Card>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2 items-center">
            <Button onClick={startRecording} disabled={status === 'recording'}>Start Recording</Button>
            <Button variant="ghost" onClick={stopRecording} disabled={status !== 'recording'}>Stop + Finish</Button>
            <div className="text-sm text-muted-foreground">Session: <span className="font-mono">{sessionId || '-'}</span></div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm">Elapsed: <span className="font-mono">{Math.floor(elapsed/60)}:{String(elapsed%60).padStart(2,'0')}</span></div>
            <div className="flex items-center gap-2">
              <div className="text-sm">Level</div>
              <div className="h-2 w-40 bg-muted rounded overflow-hidden"><div className="h-full bg-green-600" style={{ width: `${Math.round(level*100)}%` }} /></div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><h3 className="font-medium">Activity</h3></CardHeader>
        <CardContent>
          <pre className="bg-muted rounded-md p-3 max-h-72 overflow-auto whitespace-pre-wrap text-sm">{log.join('\n')}</pre>
        </CardContent>
      </Card>
    </main>
  )
}

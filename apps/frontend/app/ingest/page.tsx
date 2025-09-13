"use client"
import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiBase, authHeaders, wsUrl } from '../../lib/api'
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
  const wsRef = useRef<WebSocket | null>(null)
  const redirectedRef = useRef<boolean>(false)
  const [toast, setToast] = useState<string>('')
  const [procElapsed, setProcElapsed] = useState<number>(0)
  const [procPercent, setProcPercent] = useState<number>(0)
  const procTimerRef = useRef<any>(null)
  const audioEstSecRef = useRef<number>(0)
  const estTotalRef = useRef<number>(10)

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
      setStatus('processing')
      // Start simple progress based on estimated audio length (chunks * 3s)
      audioEstSecRef.current = Math.max(1, chunksRef.current * 3)
      // Initial estimate: audio length (seconds) scaled by 1.0x
      estTotalRef.current = Math.max(5, Math.round(audioEstSecRef.current * 1.0))
      const startTs = Date.now()
      if (procTimerRef.current) clearInterval(procTimerRef.current)
      procTimerRef.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTs) / 1000)
        setProcElapsed(elapsed)
        const pct = Math.min(95, Math.round((elapsed / estTotalRef.current) * 100))
        setProcPercent(pct)
      }, 500)

      // Open WS to listen for 'completed' event
      try {
        const token = localStorage.getItem('MOMSEZ_JWT') || ''
        const u = wsUrl(`/ws/session?session_id=${sid}&token=${encodeURIComponent(token)}`)
        const ws = new WebSocket(u)
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data)
            if (msg?.type === 'processing' && msg?.session_id === sid && typeof msg?.audio_duration === 'number') {
              // Update estimate with actual audio duration from backend
              audioEstSecRef.current = Math.max(1, Math.round(msg.audio_duration))
              estTotalRef.current = Math.max(5, Math.round(audioEstSecRef.current * 1.0))
            }
            if (msg?.type === 'completed' && msg?.session_id === sid && !redirectedRef.current) {
              setToast('Selesai — transcript siap diunduh')
              setTimeout(() => setToast(''), 2000)
              if (procTimerRef.current) { clearInterval(procTimerRef.current); procTimerRef.current = null }
              redirectedRef.current = true
              setTimeout(() => { try { router.push(`/sessions/${sid}`) } catch {} }, 600)
              try { ws.close() } catch {}
            }
          } catch {}
        }
        wsRef.current = ws
      } catch {}

      // Kick off finish request; fallback redirect if no WS event arrives shortly
      const resp = await fetch(`${apiBase()}/sessions/${sid}/finish`, { method: 'POST', headers: authHeaders() })
      if (!resp.ok) { logLine('finish failed: ' + (await resp.text())); return }
      setTimeout(async () => {
        if (!redirectedRef.current) {
          try { await resp.json() } catch {}
          setToast('Selesai — transcript siap diunduh')
          setTimeout(() => setToast(''), 1500)
          if (procTimerRef.current) { clearInterval(procTimerRef.current); procTimerRef.current = null }
          try { wsRef.current?.close() } catch {}
          redirectedRef.current = true
          try { router.push(`/sessions/${sid}`) } catch {}
        }
      }, 1200)
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
    try { wsRef.current?.close() } catch {}
    if (procTimerRef.current) { clearInterval(procTimerRef.current); procTimerRef.current = null }
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
            <Button onClick={startRecording} disabled={status === 'recording' || status === 'processing'}>Start Recording</Button>
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

      {status === 'processing' && (
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="h-4 w-4 rounded-full border-2 border-gray-300 border-t-gray-700 animate-spin" />
              <div>
                <div className="text-sm text-muted-foreground">Processing</div>
                <div className="text-sm">Merging chunks and transcribing… ({procPercent}%)</div>
                <div className="text-xs text-muted-foreground">Est. audio ~ {Math.max(1, audioEstSecRef.current)}s • Elapsed {procElapsed}s</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {toast && (
        <div className="fixed top-4 right-4 z-50">
          <div className="bg-black text-white text-sm px-3 py-2 rounded shadow">{toast}</div>
        </div>
      )}
    </main>
  )
}

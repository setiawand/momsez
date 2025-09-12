"use client"
import { useState } from 'react'
import { apiBase, authHeaders } from '../../../lib/api'

export default function StartSession() {
  const [mode, setMode] = useState<'ingest'|'device'>('ingest')
  const [deviceIndex, setDeviceIndex] = useState<number | ''>('' as any)
  const [language, setLanguage] = useState<string>('auto')
  const [result, setResult] = useState<any>(null)
  const [err, setErr] = useState('')

  const start = async () => {
    setErr(''); setResult(null)
    const body: any = { language }
    if (mode === 'ingest') body.ingest = true
    else if (deviceIndex !== '' && deviceIndex != null) body.device_index = Number(deviceIndex)
    const res = await fetch(`${apiBase()}/sessions/start`, {
      method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    })
    if (!res.ok) { setErr(await res.text()); return }
    const data = await res.json(); setResult(data)
  }

  return (
    <main style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h1>Start Session</h1>
      <div style={{ display: 'grid', gap: 8, maxWidth: 420 }}>
        <label>
          <span>Mode: </span>
          <select value={mode} onChange={e => setMode(e.target.value as any)}>
            <option value="ingest">Ingest (browser upload)</option>
            <option value="device">Device capture (server mic)</option>
          </select>
        </label>
        <label>
          <span>Language: </span>
          <select value={language} onChange={e => setLanguage(e.target.value)}>
            <option value="auto">Auto-detect</option>
            <option value="id">Indonesian (id)</option>
            <option value="en">English (en)</option>
          </select>
        </label>
        {mode === 'device' && (
          <input placeholder="device index (optional)" value={deviceIndex as any} onChange={e => setDeviceIndex(e.target.value as any)} />
        )}
        <button onClick={start}>Start</button>
        {err && <div style={{ color: 'crimson' }}>{err}</div>}
        {result && (
          <pre style={{ background: '#fafafa', padding: 12 }}>{JSON.stringify(result, null, 2)}</pre>
        )}
      </div>
    </main>
  )
}

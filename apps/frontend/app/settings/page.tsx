"use client"
import useSWR from 'swr'
import { useMemo, useState } from 'react'
import { apiBase, authHeaders } from '../../lib/api'
import { Card, CardContent, CardHeader } from '../../components/ui/card'
import { Button } from '../../components/ui/button'

const fetcher = (u: string) => fetch(u, { headers: authHeaders() }).then(r => r.json())

export default function SettingsPage() {
  const { data: settings, mutate: mutSettings } = useSWR(`${apiBase()}/settings`, fetcher)
  const { data: installed, mutate: mutInstalled } = useSWR(`${apiBase()}/models/installed`, fetcher, { refreshInterval: 5000 })
  const { data: catalog } = useSWR(`${apiBase()}/models/catalog`, fetcher)
  const { data: dl } = useSWR(`${apiBase()}/models/downloads`, fetcher, { refreshInterval: 2000 })
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const [val, setVal] = useState<{running?: boolean, result?: string}>({})
  const [uplBusy, setUplBusy] = useState(false)

  const models = useMemo(() => (installed?.models || []) as { name: string, path: string, size?: number }[], [installed])
  const downloads = (dl?.downloads || {}) as Record<string, any>

  const saveModel = async () => {
    if (!selectedModel) return
    setBusy(true)
    try {
      const payload = { chunk_model: selectedModel }
      const res = await fetch(`${apiBase()}/settings`, { method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      if (!res.ok) throw new Error(await res.text())
      await mutSettings()
    } catch (e) {
      console.error(e)
    } finally {
      setBusy(false)
    }
  }

  const download = async (name: string) => {
    try {
      await fetch(`${apiBase()}/models/download`, { method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })
      await Promise.all([mutInstalled(), mutSettings()])
    } catch {}
  }

  const uploadModel = async (file: File | null) => {
    if (!file) return
    setUplBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`${apiBase()}/models/upload`, { method: 'POST', headers: authHeaders(), body: fd })
      if (!res.ok) throw new Error(await res.text())
      await mutInstalled()
      await mutSettings()
    } catch (e) {
      console.error(e)
    } finally {
      setUplBusy(false)
    }
  }

  const validate = async () => {
    setVal({ running: true, result: '' })
    try {
      const path = selectedModel || settings?.chunk_model
      const res = await fetch(`${apiBase()}/models/validate`, { method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' }, body: JSON.stringify({ path }) })
      const data = await res.json()
      if (res.ok && data?.valid) {
        setVal({ running: false, result: '✅ Model valid' })
      } else {
        const msg = (data?.error || data?.log || 'Validation failed').toString().slice(-400)
        setVal({ running: false, result: '❌ ' + msg })
      }
    } catch (e: any) {
      setVal({ running: false, result: '❌ ' + String(e) })
    }
  }

  return (
    <main className="space-y-4">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <Card>
        <CardHeader><h3 className="font-medium">Active Model</h3></CardHeader>
        <CardContent className="space-y-3">
          <div className="text-sm text-muted-foreground">Current: <span className="font-mono">{settings?.chunk_model || '-'}</span></div>
          <div className="flex items-center gap-2">
            <select className="border rounded px-2 py-1 text-sm min-w-[300px]" value={selectedModel} onChange={e => setSelectedModel(e.target.value)}>
              <option value="">Select installed model…</option>
              {models.map(m => {
                const key = m.name.startsWith('ggml-') && m.name.endsWith('.bin') ? m.name.slice(5, -4) : m.name
                const st = downloads[key]?.status
                const label = st === 'downloading' ? `${m.name} (downloading… ${formatSize(m.size)})` : `${m.name} (${formatSize(m.size)})`
                return <option key={m.name} value={st === 'downloading' ? '' : m.path} disabled={st === 'downloading'}>{label}</option>
              })}
            </select>
            <Button onClick={saveModel} disabled={!selectedModel || busy}>Save</Button>
            <Button variant="secondary" onClick={validate} disabled={val.running}>Validate</Button>
          </div>
          {val.result && <div className="text-xs text-muted-foreground">{val.result}</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><h3 className="font-medium">Model Catalog</h3></CardHeader>
        <CardContent className="space-y-2">
          <div className="mb-3 text-sm">
            If downloads are blocked, upload a model file (.bin) directly:
            <div className="mt-2 flex items-center gap-2">
              <input type="file" accept=".bin" onChange={e => uploadModel(e.target.files?.[0] || null)} disabled={uplBusy} />
              {uplBusy && <span className="text-xs text-muted-foreground">Uploading…</span>}
            </div>
          </div>
          <div className="grid gap-2">
            {(catalog?.models || []).map((name: string) => {
              const st = downloads[name]?.status
              const exact = `ggml-${name}.bin`
              const installed = models.some(m => m.name === exact && m.size && m.size > 0) && st !== 'downloading'
              const err = st === 'error' ? (downloads[name]?.error || downloads[name]?.log || '').toString() : ''
              return (
                <div key={name} className="flex items-center justify-between border rounded px-3 py-2">
                  <div className="text-sm">
                    <div className="font-medium">{name}</div>
                    <div className="text-xs text-muted-foreground">{installed ? 'Installed' : (st || 'not installed')}</div>
                    {st === 'error' && err && (
                      <div className="text-xs text-red-600 mt-1 whitespace-pre-wrap">{err.slice(-200)}</div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button size="sm" variant="secondary" onClick={() => download(name)} disabled={installed || st === 'downloading'}>
                      {installed ? 'Installed' : (st === 'downloading' ? 'Downloading…' : 'Download')}
                    </Button>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </main>
  )
}

function formatSize(n?: number) {
  if (!n || n <= 0) return '-'
  const mb = n / (1024*1024)
  if (mb < 1024) return `${mb.toFixed(1)} MB`
  return `${(mb/1024).toFixed(2)} GB`
}

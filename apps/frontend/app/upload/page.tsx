"use client"
import { useState } from 'react'
import { apiBase, authHeaders, transcriptContentUrl, transcriptDownloadUrl } from '../../lib/api'
import { Card, CardContent, CardHeader } from '../../components/ui/card'
import { Button } from '../../components/ui/button'

export default function UploadTranscribePage() {
  const [file, setFile] = useState<File | null>(null)
  const [language, setLanguage] = useState<string>('auto')
  const [status, setStatus] = useState<'idle'|'uploading'|'processing'|'completed'|'error'>('idle')
  const [error, setError] = useState<string>('')
  const [result, setResult] = useState<{ audio_path?: string|null, transcript_path?: string|null, text?: string } | null>(null)

  const onUpload = async () => {
    setError(''); setResult(null)
    if (!file) { setError('Please select an audio file'); return }
    setStatus('uploading')
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('language', language)
      const resp = await fetch(`${apiBase()}/upload/transcribe`, { method: 'POST', headers: authHeaders(), body: fd })
      if (!resp.ok) { setStatus('error'); setError(await resp.text()); return }
      const data = await resp.json()
      setResult(data)
      setStatus('completed')
    } catch (e: any) {
      setStatus('error'); setError(String(e))
    }
  }

  return (
    <main className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Upload & Transcribe</h1>
        <div className="text-sm text-muted-foreground">Supported: webm, wav, m4a, mp3, flac, ogg/opus</div>
      </div>

      <Card>
        <CardContent className="space-y-3 py-4">
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="file"
              accept="audio/*,.webm,.wav,.m4a,.mp3,.flac,.ogg,.opus"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <label className="text-sm flex items-center gap-2">
              <span>Language</span>
              <select className="border rounded px-2 py-1 text-sm" value={language} onChange={e => setLanguage(e.target.value)}>
                <option value="auto">Auto</option>
                <option value="id">Indonesian (id)</option>
                <option value="en">English (en)</option>
              </select>
            </label>
            <Button onClick={onUpload} disabled={!file || status === 'uploading' || status === 'processing'}>
              {status === 'uploading' || status === 'processing' ? 'Processing…' : 'Upload & Transcribe'}
            </Button>
          </div>
          {error && <div className="text-sm text-red-600 whitespace-pre-wrap">{error}</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><h3 className="font-medium">Transcript</h3></CardHeader>
        <CardContent>
          {status === 'completed' && result?.text ? (
            <>
              <pre className="bg-muted rounded-md p-3 max-h-[60vh] overflow-auto whitespace-pre-wrap text-sm">{result.text}</pre>
              {result.transcript_path && (
                <div className="mt-2 text-xs"><a className="underline" href={transcriptDownloadUrl(result.transcript_path)} target="_blank" rel="noreferrer">Download .txt</a></div>
              )}
            </>
          ) : (
            <div className="text-sm text-muted-foreground">{status === 'idle' ? 'No transcript yet' : 'Waiting for results…'}</div>
          )}
        </CardContent>
      </Card>
    </main>
  )
}


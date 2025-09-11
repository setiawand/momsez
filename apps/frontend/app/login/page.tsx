"use client"
import { useState } from 'react'
import { apiBase } from '../../lib/api'

export default function LoginPage() {
  const [userId, setUserId] = useState('alice')
  const [token, setToken] = useState('')
  const [error, setError] = useState('')

  const login = async () => {
    setError('')
    try {
      const res = await fetch(`${apiBase()}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setToken(data.access_token)
      localStorage.setItem('MOMSEZ_JWT', data.access_token)
    } catch (e: any) {
      setError(String(e))
    }
  }

  return (
    <main style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h1>Login (dev)</h1>
      <div style={{ display: 'grid', gap: 8, maxWidth: 420 }}>
        <input value={userId} onChange={e => setUserId(e.target.value)} placeholder="user_id or username" />
        <button onClick={login}>Login</button>
        {error && <div style={{ color: 'crimson' }}>{error}</div>}
        {token && (
          <div>
            <div>Token saved to localStorage (MOMSEZ_JWT)</div>
            <code style={{ display: 'block', whiteSpace: 'pre-wrap' }}>{token}</code>
          </div>
        )}
      </div>
    </main>
  )
}


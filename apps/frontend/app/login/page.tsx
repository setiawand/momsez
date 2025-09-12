"use client"
import { useState } from 'react'
import { apiBase } from '../../lib/api'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Card, CardContent } from '../../components/ui/card'

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
        // Request longer token lifetime for long meetings (8 hours)
        body: JSON.stringify({ user_id: userId, exp_minutes: 480 }),
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
    <main className="space-y-4 max-w-md">
      <h1 className="text-2xl font-semibold">Login (dev)</h1>
      <Card>
        <CardContent className="space-y-3">
          <Input value={userId} onChange={e => setUserId(e.target.value)} placeholder="user_id or username" />
          <Button onClick={login}>Login</Button>
          {error && <div className="text-red-600 text-sm">{error}</div>}
          {token && (
            <div className="text-sm">
              <div>Token saved to localStorage (MOMSEZ_JWT)</div>
              <code className="block whitespace-pre-wrap">{token}</code>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  )
}

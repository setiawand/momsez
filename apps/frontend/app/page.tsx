import Link from 'next/link'

export default function Home() {
  return (
    <main style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h1>MomSez</h1>
      <p>Simple dashboard for recording and ingest sessions.</p>
      <ul style={{ display: 'grid', gap: 8, marginTop: 16 }}>
        <li><Link href="/login">Login (dev)</Link></li>
        <li><Link href="/sessions">Sessions</Link></li>
      </ul>
    </main>
  )
}


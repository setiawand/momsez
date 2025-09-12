import './globals.css'

export const metadata = {
  title: 'MomSez',
  description: 'Transcription dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-white">
        <header className="border-b">
          <div className="container mx-auto max-w-6xl px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded bg-black" />
              <div className="text-lg font-semibold tracking-tight">MomSez</div>
            </div>
            <nav className="flex items-center gap-4 text-sm text-muted-foreground">
              <a href="/" className="hover:text-black">Dashboard</a>
              <a href="/sessions" className="hover:text-black">Sessions</a>
              <a href="/ingest" className="hover:text-black">Record</a>
              <a href="/login" className="hover:text-black">Login</a>
            </nav>
          </div>
        </header>
        <div className="container mx-auto max-w-6xl px-4 py-8">
          {children}
        </div>
      </body>
    </html>
  )
}

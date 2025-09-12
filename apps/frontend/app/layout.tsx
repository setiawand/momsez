import './globals.css'

export const metadata = {
  title: 'MomSez',
  description: 'Transcription dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="container mx-auto max-w-5xl py-8">
          {children}
        </div>
      </body>
    </html>
  )
}

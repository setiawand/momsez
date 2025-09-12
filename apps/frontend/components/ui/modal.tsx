"use client"
import { ReactNode, useEffect } from 'react'

export function Modal({ open, onClose, title, children }: { open: boolean, onClose: () => void, title?: string, children: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    if (open) window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-md shadow-lg max-w-3xl w-[90%] max-h-[80vh] overflow-hidden">
        <div className="border-b px-4 py-2 flex items-center justify-between">
          <div className="font-medium truncate pr-2">{title || 'Preview'}</div>
          <button onClick={onClose} className="text-sm text-muted-foreground hover:text-black">Close</button>
        </div>
        <div className="p-4 overflow-auto">
          {children}
        </div>
      </div>
    </div>
  )
}


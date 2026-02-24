'use client'

import { useEffect, useState } from 'react'

interface Props {
  clientName: string
}

export default function ClientSwitchingOverlay({ clientName }: Props) {
  const [dots, setDots] = useState(1)

  // Animate dots
  useEffect(() => {
    const id = setInterval(() => setDots(d => (d % 3) + 1), 500)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-white dark:bg-neutral-950">
      {/* Logo */}
      <div className="mb-10 select-none">
        <span className="text-5xl font-bold tracking-tight text-neutral-900 lowercase">
          recon
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-blue-700">
            ex
          </span>
        </span>
      </div>

      {/* Spinner ring */}
      <div className="relative w-14 h-14 mb-8">
        <div className="absolute inset-0 rounded-full border-4 border-neutral-100" />
        <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-blue-600 animate-spin" />
      </div>

      {/* Client name */}
      <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400 tracking-wide">
        Loading {clientName}
        <span className="inline-block w-6 text-left">{'.'.repeat(dots)}</span>
      </p>
    </div>
  )
}

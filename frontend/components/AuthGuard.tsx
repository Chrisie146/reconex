'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated } from '@/lib/auth'

interface AuthGuardProps {
  children: React.ReactNode
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter()
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
    } else {
      setIsReady(true)
    }
  }, [router])

  // Render children immediately to prevent hydration mismatch
  // The useEffect above will redirect if not authenticated
  if (!isReady) {
    return (
      <div className="min-h-screen flex items-center justify-center" suppressHydrationWarning>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-sm text-neutral-600">Checking authentication...</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
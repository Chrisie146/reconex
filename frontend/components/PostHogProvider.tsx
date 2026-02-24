'use client'

import { useEffect, Suspense } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import { posthog, initPostHog } from '@/lib/posthog'
import { getAuthUser } from '@/lib/auth'

/**
 * Inner component that uses useSearchParams – must be wrapped in <Suspense>.
 */
function PostHogPageView() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (typeof window === 'undefined') return
    posthog.capture('$pageview', { $current_url: window.location.href })
  }, [pathname, searchParams])

  return null
}

/**
 * PostHogProvider – place inside RootLayout (client boundary).
 *
 * Responsibilities:
 *  • Initialise PostHog once on mount
 *  • Identify already-authenticated users (page refresh, direct navigation)
 *  • Listen for auth:login / auth:logout window events dispatched by lib/auth.ts
 *  • Track $pageview on every client-side route change
 */
export default function PostHogProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    initPostHog()

    // Identify user that may already be authenticated (e.g. after page refresh)
    const user = getAuthUser()
    if (user) {
      posthog.identify(String(user.user_id), {
        email: user.email,
        name: user.full_name ?? undefined,
      })
    }

    const handleLogin = () => {
      const u = getAuthUser()
      if (u) {
        posthog.identify(String(u.user_id), {
          email: u.email,
          name: u.full_name ?? undefined,
        })
      }
    }

    const handleLogout = () => {
      posthog.capture('user_logged_out')
      posthog.reset()
    }

    window.addEventListener('auth:login', handleLogin)
    window.addEventListener('auth:logout', handleLogout)
    return () => {
      window.removeEventListener('auth:login', handleLogin)
      window.removeEventListener('auth:logout', handleLogout)
    }
  }, [])

  return (
    <>
      <Suspense fallback={null}>
        <PostHogPageView />
      </Suspense>
      {children}
    </>
  )
}

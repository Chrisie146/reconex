import posthog from 'posthog-js'

/**
 * Initialise PostHog once (idempotent – safe to call multiple times).
 * Session recording is intentionally disabled.
 */
export function initPostHog(): void {
  if (typeof window === 'undefined') return
  if (posthog.__loaded) return

  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY
  if (!key || key.startsWith('phc_your')) return // silently skip if key not configured

  posthog.init(key, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com',
    capture_pageview: false, // handled manually in PostHogProvider
    capture_pageleave: true,
    autocapture: false,
    disable_session_recording: true,
    persistence: 'localStorage',
  })
}

export { posthog }

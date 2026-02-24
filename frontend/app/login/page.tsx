'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import axios from '@/lib/axiosClient'
import { setToken, setAuthUser } from '@/lib/auth'
import { Loader2 } from 'lucide-react'
import { posthog } from '@/lib/posthog'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const response = await axios.post('/auth/login', { email, password })
      const data = response.data
      setToken(data.access_token)
      setAuthUser({ user_id: data.user_id, email: data.email, full_name: data.full_name })
      posthog.capture('user_logged_in', { email: data.email })
      // Keep loading true — full-screen overlay will show during navigation
      router.push('/dashboard')
    } catch (err: any) {
      const message = err?.response?.data?.detail || 'Login failed'
      setError(message)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-neutral-950 px-4">
      {/* Full-screen loading overlay shown after successful login */}
      {loading && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600 mb-2" />
          <p className="text-sm text-neutral-500 font-medium">Signing you in…</p>
        </div>
      )}
      <div className="w-full max-w-sm">
        {/* Brand */}
        <Link href="/" className="flex items-center justify-center gap-2.5 mb-8">
          <span className="text-lg font-bold text-neutral-900 tracking-tight">recon<span className="text-blue-600">ex</span></span>
        </Link>

        {/* Card */}
        <div className="rounded-2xl bg-white dark:bg-neutral-900 ring-1 ring-neutral-200 dark:ring-neutral-700 shadow-sm p-6">
          <h1 className="text-xl font-bold text-neutral-900 dark:text-white">Sign in</h1>
          <p className="text-sm text-neutral-500 mt-1">Access your statements and reports.</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="text-[11px] font-bold uppercase tracking-widest text-neutral-500">
                Email
              </label>
              <input
                type="email"
                className="mt-1.5 w-full rounded-lg ring-1 ring-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-bold uppercase tracking-widest text-neutral-500">
                  Password
                </label>
                <Link href="/forgot-password" className="text-[11px] font-medium text-blue-600 hover:text-blue-700 transition-colors">
                  Forgot password?
                </Link>
              </div>
              <input
                type="password"
                className="mt-1.5 w-full rounded-lg ring-1 ring-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
                placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 ring-1 ring-red-200 px-3 py-2 text-sm text-red-600">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 py-2.5 text-sm font-semibold text-white transition-colors"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>
        </div>

        <p className="mt-5 text-center text-sm text-neutral-500">
          No account?{' '}
          <Link href="/register" className="font-medium text-blue-600 hover:text-blue-700 transition-colors">
            Create one
          </Link>
        </p>
      </div>
    </div>
  )
}

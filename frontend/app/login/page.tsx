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
      router.push('/dashboard')
    } catch (err: any) {
      const message = err?.response?.data?.detail || 'Login failed'
      setError(message)
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-neutral-950 px-4 overflow-hidden">
      {/* Full-screen loading overlay */}
      {loading && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-neutral-950/90 backdrop-blur-sm">
          <Loader2 className="w-6 h-6 animate-spin text-blue-400 mb-2" />
          <p className="text-sm text-neutral-400 font-medium">Signing you in…</p>
        </div>
      )}

      {/* Subtle background glow — static, no animation */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-indigo-600/[0.07] rounded-full blur-[120px] pointer-events-none" />

      <div className="relative w-full max-w-sm">
        {/* Brand */}
        <Link href="/" className="flex items-center justify-center gap-2.5 mb-8 group">
          <div className="relative">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <span className="text-white font-bold text-sm">R</span>
            </div>
            <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-blue-400 to-indigo-500 blur-md opacity-0 group-hover:opacity-40 transition-opacity duration-300" />
          </div>
          <span className="text-lg font-bold text-white tracking-tight">
            recon<span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">ex</span>
          </span>
        </Link>

        {/* Card */}
        <div className="rounded-2xl bg-neutral-900/80 border border-neutral-800 backdrop-blur-xl shadow-2xl shadow-black/40 p-6">
          <h1 className="text-xl font-bold text-white">Sign in</h1>
          <p className="text-sm text-neutral-500 mt-1">Access your statements and reports.</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="text-[11px] font-bold uppercase tracking-widest text-neutral-500">
                Email
              </label>
              <input
                type="email"
                className="mt-1.5 w-full rounded-lg border border-neutral-700/80 bg-neutral-800/50 px-3 py-2 text-sm text-white placeholder:text-neutral-600 focus:outline-none focus:border-blue-500/70 focus:ring-1 focus:ring-blue-500/50 transition-all"
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
                <Link href="/forgot-password" className="text-[11px] font-medium text-blue-400 hover:text-blue-300 transition-colors">
                  Forgot password?
                </Link>
              </div>
              <input
                type="password"
                className="mt-1.5 w-full rounded-lg border border-neutral-700/80 bg-neutral-800/50 px-3 py-2 text-sm text-white placeholder:text-neutral-600 focus:outline-none focus:border-blue-500/70 focus:ring-1 focus:ring-blue-500/50 transition-all"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {error && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2 text-sm text-red-400">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 py-2.5 text-sm font-semibold text-white transition-all duration-200 shadow-lg shadow-blue-600/20"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Signing in…
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>
        </div>

        <p className="mt-5 text-center text-sm text-neutral-600">
          No account?{' '}
          <Link href="/register" className="font-medium text-blue-400 hover:text-blue-300 transition-colors">
            Create one
          </Link>
        </p>
      </div>
    </div>
  )
}

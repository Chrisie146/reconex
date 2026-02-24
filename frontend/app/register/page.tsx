'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import axios from '@/lib/axiosClient'
import { setToken, setAuthUser } from '@/lib/auth'
import { Landmark, Loader2 } from 'lucide-react'
import { posthog } from '@/lib/posthog'

export default function RegisterPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      setLoading(false)
      return
    }

    try {
      const payload: any = { email, password }
      if (fullName.trim()) payload.full_name = fullName.trim()

      const response = await axios.post('/auth/register', payload)
      const data = response.data
      setToken(data.access_token)
      setAuthUser({ user_id: data.user_id, email: data.email, full_name: data.full_name })
      posthog.capture('user_registered', { email: data.email, full_name: data.full_name })

      // Mark as new user so dashboard shows onboarding
      if (typeof window !== 'undefined') {
        localStorage.setItem('reconex_onboarding', 'pending')
      }

      router.push('/dashboard')
    } catch (err: any) {
      const message = err?.response?.data?.detail || 'Registration failed'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-neutral-950 px-4">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <Link href="/" className="flex items-center justify-center gap-2.5 mb-8">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
            <Landmark className="w-[18px] h-[18px] text-white" />
          </div>
          <span className="text-lg font-bold text-neutral-900 tracking-tight">Recon<span className="text-blue-600">ex</span></span>
        </Link>

        {/* Card */}
        <div className="rounded-2xl bg-white dark:bg-neutral-900 ring-1 ring-neutral-200 dark:ring-neutral-700 shadow-sm p-6">
          <h1 className="text-xl font-bold text-neutral-900 dark:text-white">Create account</h1>
          <p className="text-sm text-neutral-500 mt-1">Start analyzing bank statements securely.</p>

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
              <label className="text-[11px] font-bold uppercase tracking-widest text-neutral-500">
                Full name
              </label>
              <input
                type="text"
                className="mt-1.5 w-full rounded-lg ring-1 ring-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
                placeholder="Jane Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>
            <div>
              <label className="text-[11px] font-bold uppercase tracking-widest text-neutral-500">
                Password
              </label>
              <input
                type="password"
                className="mt-1.5 w-full rounded-lg ring-1 ring-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
                placeholder="Min 8 characters"
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
                  Creating...
                </>
              ) : (
                'Create account'
              )}
            </button>
          </form>
        </div>

        <p className="mt-5 text-center text-sm text-neutral-500">
          Already have an account?{' '}
          <Link href="/login" className="font-medium text-blue-600 hover:text-blue-700 transition-colors">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}

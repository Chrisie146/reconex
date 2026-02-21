'use client'

import { useState } from 'react'
import Link from 'next/link'
import axios from '@/lib/axiosClient'
import { Landmark, Loader2, ArrowLeft, MailCheck } from 'lucide-react'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await axios.post('/auth/forgot-password', { email })
      setSubmitted(true)
    } catch (err: any) {
      // Show a generic error — never reveal whether the email exists
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 px-4">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <Link href="/" className="flex items-center justify-center gap-2.5 mb-8">
          <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center">
            <Landmark className="w-[18px] h-[18px] text-white" />
          </div>
          <span className="text-lg font-bold text-neutral-900 tracking-tight">StatementBur</span>
        </Link>

        <div className="rounded-2xl bg-white ring-1 ring-neutral-200 shadow-sm p-6">
          {submitted ? (
            /* Success state */
            <div className="text-center py-2">
              <div className="w-12 h-12 rounded-full bg-indigo-50 flex items-center justify-center mx-auto mb-4">
                <MailCheck className="w-6 h-6 text-indigo-600" />
              </div>
              <h1 className="text-xl font-bold text-neutral-900">Check your email</h1>
              <p className="text-sm text-neutral-500 mt-2 leading-relaxed">
                If <span className="font-medium text-neutral-700">{email}</span> is registered,
                you'll receive a password reset link within a few minutes.
              </p>
              <p className="text-xs text-neutral-400 mt-3">
                Don't see it? Check your spam folder.
              </p>
              <Link
                href="/login"
                className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to sign in
              </Link>
            </div>
          ) : (
            /* Form state */
            <>
              <h1 className="text-xl font-bold text-neutral-900">Forgot password?</h1>
              <p className="text-sm text-neutral-500 mt-1">
                Enter your email and we'll send you a reset link.
              </p>

              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                <div>
                  <label className="text-[11px] font-bold uppercase tracking-widest text-neutral-500">
                    Email
                  </label>
                  <input
                    type="email"
                    className="mt-1.5 w-full rounded-lg ring-1 ring-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
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
                  className="w-full flex items-center justify-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 py-2.5 text-sm font-semibold text-white transition-colors"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Sending…
                    </>
                  ) : (
                    'Send reset link'
                  )}
                </button>
              </form>
            </>
          )}
        </div>

        {!submitted && (
          <p className="mt-5 text-center text-sm text-neutral-500">
            Remember your password?{' '}
            <Link href="/login" className="font-medium text-indigo-600 hover:text-indigo-700 transition-colors">
              Sign in
            </Link>
          </p>
        )}
      </div>
    </div>
  )
}

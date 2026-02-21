'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import axios from '@/lib/axiosClient'
import { Landmark, Loader2, Eye, EyeOff, CheckCircle2, XCircle } from 'lucide-react'

// ---------------------------------------------------------------------------
// Password-strength helpers (mirrors the backend rules)
// ---------------------------------------------------------------------------
interface StrengthResult {
  score: number        // 0–4
  label: string
  color: string        // Tailwind bg class
  labelColor: string   // Tailwind text class
}

function getStrength(password: string): StrengthResult {
  let score = 0
  if (password.length >= 8) score++
  if (/[A-Z]/.test(password)) score++
  if (/[a-z]/.test(password)) score++
  if (/\d/.test(password)) score++
  if (/[^A-Za-z0-9]/.test(password)) score++

  if (score <= 1) return { score, label: 'Very weak',  color: 'bg-red-500',    labelColor: 'text-red-600' }
  if (score === 2) return { score, label: 'Weak',       color: 'bg-orange-400', labelColor: 'text-orange-500' }
  if (score === 3) return { score, label: 'Fair',       color: 'bg-yellow-400', labelColor: 'text-yellow-600' }
  if (score === 4) return { score, label: 'Good',       color: 'bg-blue-500',   labelColor: 'text-blue-600' }
  return              { score, label: 'Strong',      color: 'bg-green-500',  labelColor: 'text-green-600' }
}

const REQUIREMENTS = [
  { label: 'At least 8 characters',     test: (p: string) => p.length >= 8 },
  { label: 'An uppercase letter (A–Z)', test: (p: string) => /[A-Z]/.test(p) },
  { label: 'A lowercase letter (a–z)',  test: (p: string) => /[a-z]/.test(p) },
  { label: 'A number (0–9)',            test: (p: string) => /\d/.test(p) },
  { label: 'A special character',       test: (p: string) => /[^A-Za-z0-9]/.test(p) },
]

// ---------------------------------------------------------------------------
// Inner component (needs useSearchParams — must be inside Suspense)
// ---------------------------------------------------------------------------
function ResetPasswordForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token') ?? ''

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const strength = getStrength(newPassword)

  // Redirect if token is missing entirely
  useEffect(() => {
    if (!token) {
      router.replace('/forgot-password')
    }
  }, [token, router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)
    try {
      await axios.post('/auth/reset-password', {
        token,
        new_password: newPassword,
        new_password_confirm: confirmPassword,
      })
      setSuccess(true)
      // Give the user a moment to read the success message, then redirect
      setTimeout(() => router.push('/login'), 3000)
    } catch (err: any) {
      const message =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        'Something went wrong. Please try again or request a new reset link.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="text-center py-2">
        <div className="w-12 h-12 rounded-full bg-green-50 flex items-center justify-center mx-auto mb-4">
          <CheckCircle2 className="w-6 h-6 text-green-600" />
        </div>
        <h1 className="text-xl font-bold text-neutral-900">Password reset!</h1>
        <p className="text-sm text-neutral-500 mt-2 leading-relaxed">
          Your password has been updated. Redirecting you to sign in…
        </p>
        <Link
          href="/login"
          className="mt-4 inline-block text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
        >
          Go to sign in
        </Link>
      </div>
    )
  }

  return (
    <>
      <h1 className="text-xl font-bold text-neutral-900">Set new password</h1>
      <p className="text-sm text-neutral-500 mt-1">
        Choose a strong password for your account.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {/* New password */}
        <div>
          <label className="text-[11px] font-bold uppercase tracking-widest text-neutral-500">
            New password
          </label>
          <div className="relative mt-1.5">
            <input
              type={showNew ? 'text' : 'password'}
              className="w-full rounded-lg ring-1 ring-neutral-200 bg-neutral-50 px-3 py-2 pr-10 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow"
              placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
            <button
              type="button"
              onClick={() => setShowNew((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
              tabIndex={-1}
            >
              {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>

          {/* Strength meter */}
          {newPassword.length > 0 && (
            <div className="mt-2 space-y-1.5">
              {/* Bar */}
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div
                    key={i}
                    className={`h-1 flex-1 rounded-full transition-colors ${
                      i <= strength.score ? strength.color : 'bg-neutral-200'
                    }`}
                  />
                ))}
              </div>
              <p className={`text-xs font-medium ${strength.labelColor}`}>{strength.label}</p>

              {/* Requirements checklist */}
              <ul className="mt-1 space-y-0.5">
                {REQUIREMENTS.map((r) => {
                  const met = r.test(newPassword)
                  return (
                    <li key={r.label} className="flex items-center gap-1.5 text-xs">
                      {met ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-neutral-300 shrink-0" />
                      )}
                      <span className={met ? 'text-neutral-600' : 'text-neutral-400'}>{r.label}</span>
                    </li>
                  )
                })}
              </ul>
            </div>
          )}
        </div>

        {/* Confirm password */}
        <div>
          <label className="text-[11px] font-bold uppercase tracking-widest text-neutral-500">
            Confirm password
          </label>
          <div className="relative mt-1.5">
            <input
              type={showConfirm ? 'text' : 'password'}
              className="w-full rounded-lg ring-1 ring-neutral-200 bg-neutral-50 px-3 py-2 pr-10 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow"
              placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
            <button
              type="button"
              onClick={() => setShowConfirm((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
              tabIndex={-1}
            >
              {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {/* Inline match indicator */}
          {confirmPassword.length > 0 && (
            <p className={`mt-1 text-xs font-medium ${
              confirmPassword === newPassword ? 'text-green-600' : 'text-red-500'
            }`}>
              {confirmPassword === newPassword ? 'Passwords match' : 'Passwords do not match'}
            </p>
          )}
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
              Resetting…
            </>
          ) : (
            'Reset password'
          )}
        </button>
      </form>
    </>
  )
}

// ---------------------------------------------------------------------------
// Page export — wraps the form in Suspense (required for useSearchParams)
// ---------------------------------------------------------------------------
export default function ResetPasswordPage() {
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
          <Suspense fallback={
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
            </div>
          }>
            <ResetPasswordForm />
          </Suspense>
        </div>

        <p className="mt-5 text-center text-sm text-neutral-500">
          <Link href="/forgot-password" className="font-medium text-indigo-600 hover:text-indigo-700 transition-colors">
            Request a new reset link
          </Link>
        </p>
      </div>
    </div>
  )
}

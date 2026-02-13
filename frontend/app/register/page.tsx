'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from '@/lib/axiosClient'
import { setToken, setAuthUser } from '@/lib/auth'

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

    // Client-side validation
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      setLoading(false)
      return
    }

    try {
      const payload: any = {
        email,
        password,
      }
      if (fullName.trim()) {
        payload.full_name = fullName.trim()
      }
      const response = await axios.post('/auth/register', payload)
      const data = response.data
      setToken(data.access_token)
      setAuthUser({ user_id: data.user_id, email: data.email, full_name: data.full_name })
      router.push('/dashboard')
    } catch (err: any) {
      const message = err?.response?.data?.detail || 'Registration failed'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 px-4">
      <div className="w-full max-w-md rounded-xl border bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold">Create account</h1>
        <p className="text-sm text-neutral-500 mt-1">Start analyzing bank statements securely.</p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="text-sm font-medium">Email</label>
            <input
              type="email"
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-sm font-medium">Full name</label>
            <input
              type="text"
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Password</label>
            <input
              type="password"
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <div className="text-sm text-red-600">{error}</div>}

          <button
            type="submit"
            className="w-full rounded-md bg-blue-600 py-2 text-white text-sm font-medium hover:bg-blue-700"
            disabled={loading}
          >
            {loading ? 'Creating...' : 'Create account'}
          </button>
        </form>

        <div className="mt-4 text-sm">
          <span className="text-neutral-500">Already have an account?</span>{' '}
          <a className="text-blue-600 hover:underline" href="/login">Sign in</a>
        </div>
      </div>
    </div>
  )
}

import { getToken, clearToken, clearAuthUser } from './auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function apiFetch(input: string, init: RequestInit = {}): Promise<any> {
  const token = getToken()
  const headers = new Headers(init.headers || {})
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const url = input.startsWith('http') ? input : `${API_BASE_URL}${input}`
  const response = await fetch(url, { ...init, headers })

  if (response.status === 401) {
    clearToken()
    clearAuthUser()
  }

  if (!response.ok) {
    const text = await response.text().catch(() => 'Request failed')
    throw new Error(text || `HTTP ${response.status}`)
  }

  return response.json()
}

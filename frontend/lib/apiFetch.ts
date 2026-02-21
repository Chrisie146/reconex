import { getToken, clearToken, clearAuthUser } from './auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function apiFetch(input: string, init: RequestInit = {}): Promise<any> {
  const token = getToken()
  const headers = new Headers(init.headers || {})
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const url = input.startsWith('http') ? input : `${API_BASE_URL}${input}`
  const response = await fetch(url, { 
    ...init, 
    headers,
    credentials: 'include'  // Include credentials for CORS
  })

  if (response.status === 401) {
    clearToken()
    clearAuthUser()
  }

  if (!response.ok) {
    try {
      const contentType = response.headers.get('content-type')
      let errorMessage = `HTTP ${response.status}`
      
      if (contentType?.includes('application/json')) {
        const errorData = await response.json()
        errorMessage = errorData.detail || errorData.message || errorMessage
      } else if (contentType?.includes('text/')) {
        errorMessage = await response.text() || errorMessage
      }
      
      throw new Error(errorMessage)
    } catch (e: any) {
      throw new Error(e?.message || `HTTP ${response.status}`)
    }
  }

  try {
    return await response.json()
  } catch (e) {
    // If response isn't JSON, return the text
    const text = await response.text()
    return text || {}
  }
}

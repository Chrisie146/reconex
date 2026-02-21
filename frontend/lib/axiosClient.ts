import axios from 'axios'
import { getToken, clearToken, clearAuthUser } from './auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,  // Enable credentials for CORS
})

client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearToken()
      clearAuthUser()
      // Redirect to login if we're in the browser
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    }
    
    // Improve error message extraction
    const errorMessage = 
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.message ||
      'Request failed'
    
    return Promise.reject(new Error(errorMessage))
  }
)

export default client

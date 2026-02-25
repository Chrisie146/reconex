/**
 * Centralized API base URL — single source of truth for all HTTP calls.
 * All components and lib files should import from here instead of reading
 * NEXT_PUBLIC_API_URL directly so there is only one fallback to update.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

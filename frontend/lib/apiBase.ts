/**
 * Centralized API base URL — single source of truth for all HTTP calls.
 * All components and lib files should import from here instead of reading
 * NEXT_PUBLIC_API_URL directly so there is only one fallback to update.
 *
 * In production on Railway, set NEXT_PUBLIC_API_URL to the backend service URL
 * (e.g. https://reconex-api-production.up.railway.app).
 * If not set (or same as frontend domain), rewrites in next.config.js proxy
 * the requests to BACKEND_URL server-side, so the empty string base is correct.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

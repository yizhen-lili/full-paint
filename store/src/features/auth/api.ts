// Auth API client wrappers
// Note: openapi-fetch typed client awaits `pnpm gen:api` to populate schema.ts.
// For now we use raw fetch with explicit types matching backend MeResponse.
// Source: backend/auth/schemas/response.py:13-22

export interface MeResponse {
  id: string
  name: string
  email: string
  pending_email: string | null
  role: string
  gender: string | null
  birthday: string | null
}

const API_BASE = '/api/v1'

/**
 * GET /auth/me — returns current user or null if 401 (visitor mode).
 * Other errors are thrown for the caller to handle.
 */
export async function fetchMe(): Promise<MeResponse | null> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    credentials: 'include',
  })
  if (res.status === 401) return null
  if (!res.ok) throw new Error(`fetchMe failed: ${res.status} ${res.statusText}`)
  return (await res.json()) as MeResponse
}

/**
 * POST /auth/logout — clears server-side cookie.
 */
export async function logout(): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!res.ok && res.status !== 401) {
    throw new Error(`logout failed: ${res.status}`)
  }
}

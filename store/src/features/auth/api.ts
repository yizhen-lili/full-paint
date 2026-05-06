// Auth API client wrappers
// Source: backend/auth/router.py:32-79 (customer endpoints)

export interface MeResponse {
  id: string
  name: string
  email: string
  pending_email: string | null
  role: string
  gender: string | null
  birthday: string | null
}

export interface LoginResponse {
  id: string
  name: string
  role: string
}

export interface MessageResponse {
  message: string
}

export interface VerifyEmailResponse {
  token_type: 'register' | 'email_change'
}

const API_BASE = '/api/v1'

export interface ApiError extends Error {
  status: number
  detail: string
}

async function jsonRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  })
  if (!res.ok) {
    const detail = await res
      .json()
      .then((b) => b?.detail ?? b?.message ?? `${res.status}`)
      .catch(() => `${res.status}`)
    const err = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail)) as ApiError
    err.status = res.status
    err.detail = typeof detail === 'string' ? detail : JSON.stringify(detail)
    throw err
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

/** GET /auth/me — 401 → null（訪客）；其他錯誤丟出 */
export async function fetchMe(): Promise<MeResponse | null> {
  const res = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' })
  if (res.status === 401) return null
  if (!res.ok) throw new Error(`fetchMe failed: ${res.status} ${res.statusText}`)
  return (await res.json()) as MeResponse
}

/** POST /auth/login → set cookie */
export async function login(
  email: string,
  password: string,
): Promise<LoginResponse> {
  return jsonRequest<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

/** POST /auth/logout */
export async function logout(): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!res.ok && res.status !== 401) {
    throw new Error(`logout failed: ${res.status}`)
  }
}

/** POST /auth/register → 201 + email 寄出 */
export async function register(
  name: string,
  email: string,
  password: string,
): Promise<MessageResponse> {
  return jsonRequest<MessageResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  })
}

/** POST /auth/verify-email */
export async function verifyEmail(token: string): Promise<VerifyEmailResponse> {
  return jsonRequest<VerifyEmailResponse>('/auth/verify-email', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
}

/** POST /auth/resend-verification */
export async function resendVerification(email: string): Promise<MessageResponse> {
  return jsonRequest<MessageResponse>('/auth/resend-verification', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

/** POST /auth/forgot-password */
export async function forgotPassword(email: string): Promise<MessageResponse> {
  return jsonRequest<MessageResponse>('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

/** POST /auth/reset-password */
export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<MessageResponse> {
  return jsonRequest<MessageResponse>('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, new_password: newPassword }),
  })
}

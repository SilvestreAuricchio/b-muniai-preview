const BASE = '/bff'

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (res.status === 401) {
    const err = (data as Record<string, string>).error ?? ''
    window.location.replace(
      err === 'session_revoked' ? '/?auth_error=session_revoked' : '/?auth_error=unauthorized'
    )
    return new Promise(() => {}) // suspend — redirect is in flight
  }
  if (!res.ok) throw Object.assign(new Error((data as Record<string, string>).error ?? 'Request failed'), { status: res.status, data })
  return data as T
}

export const api = {
  get:    <T>(path: string)                  => req<T>('GET',    path),
  post:   <T>(path: string, body: unknown)   => req<T>('POST',   path, body),
  put:    <T>(path: string, body: unknown)   => req<T>('PUT',    path, body),
  delete: <T>(path: string)                  => req<T>('DELETE', path),
}

const BASE = '/bff'

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  const data = await res.json()
  if (!res.ok) throw Object.assign(new Error(data.error ?? 'Request failed'), { status: res.status, data })
  return data as T
}

export const api = {
  get:    <T>(path: string)                  => req<T>('GET',    path),
  post:   <T>(path: string, body: unknown)   => req<T>('POST',   path, body),
  delete: <T>(path: string)                  => req<T>('DELETE', path),
}

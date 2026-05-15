import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export type UserRole = 'SA-root' | 'Scheduler' | 'Mediciner'

interface AuthUser {
  uuid:        string
  name:        string
  email:       string
  role:        UserRole
  hospitalIds: string[]
}

interface AuthContextValue {
  user:    AuthUser | null
  ready:   boolean
  country: string       // ISO-3166-1 alpha-2, drives tax ID format (default "BR")
  logout:  () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user,    setUser]    = useState<AuthUser | null>(null)
  const [ready,   setReady]   = useState(false)
  const [country, setCountry] = useState('BR')

  useEffect(() => {
    fetch('/bff/auth/me', { credentials: 'include' })
      .then(async (r) => {
        if (r.status === 401) {
          const body = await r.json().catch(() => ({}))
          if (body.error === 'session_revoked') {
            window.location.replace('/?auth_error=session_revoked')
          }
          return null
        }
        return r.ok ? r.json() : null
      })
      .then((data) => {
        if (data?.sub) {
          setUser({
            uuid:        data.sub,
            name:        data.name,
            email:       data.email,
            role:        data.role as UserRole,
            hospitalIds: [],
          })
          fetch('/bff/config', { credentials: 'include' })
            .then((r) => (r.ok ? r.json() : null))
            .then((cfg) => { if (cfg?.country) setCountry(cfg.country) })
            .catch(() => {})
        }
      })
      .catch(() => {})
      .finally(() => setReady(true))
  }, [])

  // Sliding session: refresh the JWT every 44 minutes (half of 88-min TTL)
  useEffect(() => {
    if (!user) return
    const id = setInterval(async () => {
      try {
        const r = await fetch('/bff/auth/refresh', { credentials: 'include' })
        if (r.status === 401) {
          const body = await r.json().catch(() => ({}))
          if (body.error === 'session_revoked') {
            window.location.replace('/?auth_error=session_revoked')
          } else {
            setUser(null)
          }
        }
      } catch { /* network error — keep session alive until next tick */ }
    }, 44 * 60 * 1000)
    return () => clearInterval(id)
  }, [user])

  async function logout() {
    await fetch('/bff/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {})
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, ready, country, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

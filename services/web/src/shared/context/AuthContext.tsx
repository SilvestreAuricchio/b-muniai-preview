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
  logout:  () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user,  setUser]  = useState<AuthUser | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    fetch('/bff/auth/me', { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.sub) {
          setUser({
            uuid:        data.sub,
            name:        data.name,
            email:       data.email,
            role:        data.role as UserRole,
            hospitalIds: [],
          })
        }
      })
      .catch(() => {})
      .finally(() => setReady(true))
  }, [])

  async function logout() {
    await fetch('/bff/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {})
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, ready, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

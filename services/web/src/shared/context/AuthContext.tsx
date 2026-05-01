import { createContext, useContext, useState, ReactNode } from 'react'

export type UserRole = 'SA-root' | 'Scheduler' | 'Mediciner'

interface AuthUser {
  uuid: string
  name: string
  role: UserRole
  hospitalIds: string[]
}

interface AuthContextValue {
  user: AuthUser | null
  login: (user: AuthUser) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>({
    uuid: 'demo-uuid',
    name: 'Demo SA',
    role: 'SA-root',
    hospitalIds: [],
  })

  return (
    <AuthContext.Provider
      value={{ user, login: setUser, logout: () => setUser(null) }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

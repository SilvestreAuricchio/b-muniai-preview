import { useState, useEffect, useRef } from 'react'
import { NavLink } from 'react-router-dom'
import { RedCross } from '@/shared/components/RedCross'
import { useAuth } from '@/shared/context/AuthContext'

const navItems = [
  { to: '/',        label: 'Dashboard',  icon: '▦' },
  { to: '/crud',    label: 'Management', icon: '⊟' },
  { to: '/reports', label: 'Reports',    icon: '▣' },
  { to: '/logs',    label: 'Audit Log',  icon: '≡' },
]

const adminOnly = [
  { to: '/crud/hospitals',   label: 'Hospitals' },
  { to: '/crud/users',       label: 'Users' },
  { to: '/crud/departments', label: 'Departments' },
]

export function Sidebar() {
  const { user, logout } = useAuth()
  const isSA = user?.role === 'SA-root'
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    if (menuOpen) document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [menuOpen])

  return (
    <aside className="flex h-full w-56 flex-col border-r border-gray-200 bg-white">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-gray-200 px-5">
        <span className="text-brand-600">
          <RedCross size={28} />
        </span>
        <span className="text-lg font-semibold tracking-tight text-gray-900">
          Muni<span className="text-brand-600">AI</span>
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {navItems.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-50 text-brand-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            <span className="text-base leading-none">{icon}</span>
            {label}
          </NavLink>
        ))}

        {isSA && (
          <>
            <div className="mt-4 mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
              Admin
            </div>
            {adminOnly.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                    isActive
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-gray-500 hover:bg-gray-100 hover:text-gray-800'
                  }`
                }
              >
                <span className="ml-2 h-1.5 w-1.5 rounded-full bg-gray-300 flex-shrink-0" />
                {label}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      {/* User strip */}
      <div ref={menuRef} className="relative border-t border-gray-200 p-3">
        {/* Dropdown menu — opens upward */}
        {menuOpen && (
          <div className="absolute bottom-full left-3 right-3 mb-2 rounded-lg border border-gray-200 bg-white shadow-lg overflow-hidden z-50">
            <div className="px-3 py-2 border-b border-gray-100">
              <p className="text-xs font-medium text-gray-900 truncate">{user?.name}</p>
              <p className="text-xs text-gray-400 truncate">{user?.email}</p>
            </div>
            <div className="py-1">
              <button
                onClick={() => { setMenuOpen(false); logout() }}
                className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                Sign out
              </button>
            </div>
          </div>
        )}

        {/* Trigger */}
        <button
          onClick={() => setMenuOpen((o) => !o)}
          className="flex w-full items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-gray-100 transition-colors"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-brand-700 text-xs font-semibold flex-shrink-0">
            {user?.name.slice(0, 2).toUpperCase() ?? '??'}
          </div>
          <div className="min-w-0 flex-1 text-left">
            <p className="truncate text-sm font-medium text-gray-900">{user?.name}</p>
            <p className="truncate text-xs text-gray-400">{user?.role}</p>
          </div>
          <span className="text-gray-400 text-xs">···</span>
        </button>
      </div>
    </aside>
  )
}

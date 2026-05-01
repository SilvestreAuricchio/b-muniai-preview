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
  const { user } = useAuth()
  const isSA = user?.role === 'SA-root'

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
      <div className="border-t border-gray-200 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-brand-700 text-xs font-semibold flex-shrink-0">
            {user?.name.slice(0, 2).toUpperCase() ?? '??'}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-gray-900">{user?.name}</p>
            <p className="truncate text-xs text-gray-400">{user?.role}</p>
          </div>
        </div>
      </div>
    </aside>
  )
}

import { RedCross } from '@/shared/components/RedCross'
import { useAuth } from '@/shared/context/AuthContext'

interface Props {
  title: string
  subtitle?: string
}

export function Header({ title, subtitle }: Props) {
  const { user, logout } = useAuth()

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      <div>
        <h1 className="text-base font-semibold text-gray-900">{title}</h1>
        {subtitle && <p className="text-xs text-gray-400">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">
        {user && (
          <span className="text-xs text-gray-500">{user.name}</span>
        )}
        <button
          onClick={logout}
          className="text-xs text-gray-400 hover:text-red-600 hover:underline"
        >
          Sign out
        </button>
        <div className="flex items-center gap-2 text-brand-600 opacity-20">
          <RedCross size={20} />
        </div>
      </div>
    </header>
  )
}

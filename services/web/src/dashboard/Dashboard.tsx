import { Header } from '@/shell/Header'
import { InsightCard } from './InsightCard'
import { useAuth } from '@/shared/context/AuthContext'
import { RedCross } from '@/shared/components/RedCross'

const saCards = [
  { label: 'Hospitals',         value: 12,   detail: '3 added this month',      accent: false, icon: '⊞' },
  { label: 'Active Medicineres',value: 248,  detail: '14 pending KYC',          accent: true,  icon: '✚' },
  { label: 'Schedulers',        value: 31,   detail: 'Across all hospitals',    accent: false, icon: '⊟' },
  { label: 'Open Slots',        value: 87,   detail: 'Unfilled in next 7 days', accent: true,  icon: '▣' },
  { label: 'Pending Users',     value: 5,    detail: 'Awaiting OTP activation', accent: false, icon: '⊙' },
  { label: 'Audit Events (24h)',value: 1204, detail: 'Logged to MongoDB',       accent: false, icon: '≡' },
]

const schedulerCards = [
  { label: 'My Hospitals',      value: 2,    detail: 'Active scope',            accent: false, icon: '⊞' },
  { label: 'Medicineres',       value: 38,   detail: 'Across my hospitals',     accent: true,  icon: '✚' },
  { label: 'Open Slots',        value: 14,   detail: 'Next 7 days',             accent: true,  icon: '▣' },
  { label: 'Filled Rate',       value: '84%',detail: 'This week',               accent: false, icon: '◈' },
]

const medicinerCards = [
  { label: 'My Slots',          value: 6,    detail: 'Upcoming assignments',    accent: true,  icon: '▣' },
  { label: 'Hours This Month',  value: 72,   detail: 'Across all hospitals',    accent: false, icon: '◷' },
  { label: 'Next Shift',        value: 'Tomorrow', detail: 'UTI — Hospital São Lucas', accent: true, icon: '✚' },
]

const cardsByRole = {
  'SA-root':    saCards,
  'Scheduler':  schedulerCards,
  'Mediciner':  medicinerCards,
}

export function Dashboard() {
  const { user } = useAuth()
  const cards = cardsByRole[user?.role ?? 'SA-root']

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Dashboard"
        subtitle={`Welcome back, ${user?.name ?? '—'}`}
      />

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {/* KPI grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {cards.map((c) => (
            <InsightCard key={c.label} {...c} />
          ))}
        </div>

        {/* Quick-action strip */}
        <div className="mt-8">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-gray-400">
            Quick Actions
          </p>
          <div className="flex flex-wrap gap-3">
            {user?.role === 'SA-root' && (
              <>
                <QuickAction label="Add Hospital"    to="/crud/hospitals/new" />
                <QuickAction label="Invite User"     to="/crud/users/new" />
                <QuickAction label="View Audit Log"  to="/logs" />
              </>
            )}
            {user?.role === 'Scheduler' && (
              <>
                <QuickAction label="Create Slot"     to="/crud/slots/new" />
                <QuickAction label="Manage Medicineres" to="/crud/users" />
              </>
            )}
            {user?.role === 'Mediciner' && (
              <>
                <QuickAction label="View My Slots"   to="/crud/slots" />
                <QuickAction label="Update Profile"  to="/crud/users/me" />
              </>
            )}
          </div>
        </div>

        {/* Brand watermark */}
        <div className="mt-12 flex items-center gap-3 text-gray-200 select-none">
          <RedCross size={36} />
          <span className="text-2xl font-bold tracking-tight">
            Muni<span className="text-gray-300">AI</span>
          </span>
        </div>
      </div>
    </div>
  )
}

function QuickAction({ label, to }: { label: string; to: string }) {
  return (
    <a
      href={to}
      onClick={(e) => e.preventDefault()}
      className="btn-ghost border border-gray-200 text-gray-700 hover:border-brand-200 hover:text-brand-700 hover:bg-brand-50"
    >
      {label}
    </a>
  )
}

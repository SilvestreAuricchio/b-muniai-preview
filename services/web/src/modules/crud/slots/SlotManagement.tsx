import { useEffect, useState, useCallback } from 'react'
import { Header } from '@/shell/Header'
import { api } from '@/shared/api'
import { CreateSlotModal } from './CreateSlotModal'
import { EditSlotModal } from './EditSlotModal'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SlotRow {
  uuid:          string
  hospital_uuid: string
  department:    string
  type:          string
  date:          string
  mediciner_crm: string | null
  created_by:    string
  created_at:    string
}

interface SlotsPage {
  items:    SlotRow[]
  total:    number
  page:     number
  per_page: number
  pages:    number
}

// ── Badge helpers ─────────────────────────────────────────────────────────────

const TYPE_COLORS: Record<string, string> = {
  PM: 'bg-blue-100 text-blue-700',
  PE: 'bg-purple-100 text-purple-700',
  CC: 'bg-red-100 text-red-700',
  CM: 'bg-green-100 text-green-700',
}

function TypeBadge({ type }: { type: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${TYPE_COLORS[type] ?? 'bg-gray-100 text-gray-600'}`}>
      {type}
    </span>
  )
}

function DeptTag({ dept }: { dept: string }) {
  return (
    <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium bg-gray-100 text-gray-600">
      {dept}
    </span>
  )
}

// ── Date window helpers ───────────────────────────────────────────────────────

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function addDays(d: Date, n: number): Date {
  const r = new Date(d)
  r.setDate(r.getDate() + n)
  return r
}

function mondayOf(d: Date): Date {
  const r = new Date(d)
  const day = r.getDay() // 0=Sun
  const diff = day === 0 ? -6 : 1 - day
  r.setDate(r.getDate() + diff)
  return r
}

function sundayOf(d: Date): Date {
  return addDays(mondayOf(d), 6)
}

// ── Agenda period options ─────────────────────────────────────────────────────

type PeriodKey = 'week' | 'plus2' | 'plus4' | 'plus8' | '1week' | '2weeks' | '1month' | 'custom'

const PERIOD_LABELS: { key: PeriodKey; label: string }[] = [
  { key: 'week',    label: 'Current Week' },
  { key: 'plus2',   label: '+2 days' },
  { key: 'plus4',   label: '+4 days' },
  { key: 'plus8',   label: '+8 days' },
  { key: '1week',   label: '1 Week' },
  { key: '2weeks',  label: '2 Weeks' },
  { key: '1month',  label: '1 Month' },
  { key: 'custom',  label: 'Custom' },
]

function computePeriod(key: PeriodKey, today: Date): [Date, Date] {
  switch (key) {
    case 'week':   return [mondayOf(today), sundayOf(today)]
    case 'plus2':  return [today, addDays(today, 2)]
    case 'plus4':  return [today, addDays(today, 4)]
    case 'plus8':  return [today, addDays(today, 8)]
    case '1week':  return [today, addDays(today, 7)]
    case '2weeks': return [today, addDays(today, 14)]
    case '1month': return [today, addDays(today, 30)]
    default:       return [today, addDays(today, 7)]
  }
}

// ── Table view ────────────────────────────────────────────────────────────────

interface TableViewProps {
  page:       number
  perPage:    number
  fromDate:   Date
  toDate:     Date
  onPrev:     () => void
  onNext:     () => void
  onToday:    () => void
  onSetFrom:  (d: Date) => void
  onSetTo:    (d: Date) => void
  onEdit:     (s: SlotRow) => void
  onDelete:   (s: SlotRow) => void
  onPageChange: (p: number) => void
  slots:      SlotRow[]
  total:      number
  pages:      number
  loading:    boolean
}

function TableView({
  page, fromDate, toDate,
  onPrev, onNext, onToday, onEdit, onDelete, onPageChange,
  slots, total, pages, loading,
}: TableViewProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <button onClick={onPrev} className="btn-ghost text-sm border border-gray-200 px-3 py-1.5">← Prev</button>
        <button onClick={onToday} className="btn-ghost text-sm border border-gray-200 px-3 py-1.5">Today</button>
        <button onClick={onNext} className="btn-ghost text-sm border border-gray-200 px-3 py-1.5">Next →</button>
        <span className="text-xs text-gray-400 ml-2">
          {isoDate(fromDate)} – {isoDate(toDate)}
        </span>
        <span className="ml-auto text-xs text-gray-400">{total} slot{total !== 1 ? 's' : ''}</span>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : slots.length === 0 ? (
        <div className="card p-8 text-center text-gray-400">
          <p className="text-sm">No slots in this period.</p>
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Department</th>
                <th className="px-4 py-3">Hospital</th>
                <th className="px-4 py-3">CRM</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {slots.map((s) => (
                <tr key={s.uuid} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-4 py-3 font-mono text-gray-700">{s.date}</td>
                  <td className="px-4 py-3"><TypeBadge type={s.type} /></td>
                  <td className="px-4 py-3"><DeptTag dept={s.department} /></td>
                  <td className="px-4 py-3 text-gray-600 truncate max-w-[160px]">{s.hospital_uuid}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{s.mediciner_crm ?? '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => onEdit(s)}
                        className="text-brand-600 hover:text-brand-700"
                        title="Edit"
                      >
                        <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                          <path d="M2.695 14.763l-1.262 3.154a.5.5 0 0 0 .65.65l3.155-1.262a4 4 0 0 0 1.343-.885L17.5 5.5a2.121 2.121 0 0 0-3-3L3.58 13.42a4 4 0 0 0-.885 1.343Z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => onDelete(s)}
                        className="text-red-400 hover:text-red-600"
                        title="Delete"
                      >
                        <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                          <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 0 0 6 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 1 0 .23 1.482l.149-.022.841 10.518A2.75 2.75 0 0 0 7.596 19h4.807a2.75 2.75 0 0 0 2.742-2.53l.841-10.52.149.023a.75.75 0 0 0 .23-1.482A41.03 41.03 0 0 0 14 3.193V3.75A2.75 2.75 0 0 0 11.25 1h-2.5ZM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4ZM8.58 7.72a.75.75 0 0 0-1.5.06l.3 7.5a.75.75 0 1 0 1.5-.06l-.3-7.5Zm4.34.06a.75.75 0 1 0-1.5-.06l-.3 7.5a.75.75 0 1 0 1.5.06l.3-7.5Z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="btn-ghost text-sm border border-gray-200 px-3 py-1.5 disabled:opacity-40"
          >
            ← Prev
          </button>
          <span className="text-sm text-gray-500">Page {page} of {pages}</span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= pages}
            className="btn-ghost text-sm border border-gray-200 px-3 py-1.5 disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}

// ── Day detail slide-over ─────────────────────────────────────────────────────

function DaySlideOver({
  dayLabel,
  slots,
  onClose,
  onEdit,
  onDelete,
}: {
  dayLabel: string
  slots: SlotRow[]
  onClose: () => void
  onEdit: (s: SlotRow) => void
  onDelete: (s: SlotRow) => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onClick={onClose}>
      <div
        className="relative h-full w-full max-w-sm bg-white shadow-xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-900">{dayLabel}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">✕</button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {slots.length === 0 ? (
            <p className="text-sm text-gray-400">No slots on this day.</p>
          ) : (
            slots.map((s) => (
              <div key={s.uuid} className="flex items-start justify-between gap-3 rounded-lg border border-gray-100 p-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <TypeBadge type={s.type} />
                    <DeptTag dept={s.department} />
                  </div>
                  {s.mediciner_crm && (
                    <p className="text-xs text-gray-500 font-mono">{s.mediciner_crm}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => onEdit(s)} className="text-brand-600 hover:text-brand-700">
                    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                      <path d="M2.695 14.763l-1.262 3.154a.5.5 0 0 0 .65.65l3.155-1.262a4 4 0 0 0 1.343-.885L17.5 5.5a2.121 2.121 0 0 0-3-3L3.58 13.42a4 4 0 0 0-.885 1.343Z" />
                    </svg>
                  </button>
                  <button onClick={() => onDelete(s)} className="text-red-400 hover:text-red-600">
                    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                      <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 0 0 6 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 1 0 .23 1.482l.149-.022.841 10.518A2.75 2.75 0 0 0 7.596 19h4.807a2.75 2.75 0 0 0 2.742-2.53l.841-10.52.149.023a.75.75 0 0 0 .23-1.482A41.03 41.03 0 0 0 14 3.193V3.75A2.75 2.75 0 0 0 11.25 1h-2.5ZM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4ZM8.58 7.72a.75.75 0 0 0-1.5.06l.3 7.5a.75.75 0 1 0 1.5-.06l-.3-7.5Zm4.34.06a.75.75 0 1 0-1.5-.06l-.3 7.5a.75.75 0 1 0 1.5.06l.3-7.5Z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

// ── Agenda view ───────────────────────────────────────────────────────────────

const DAY_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function AgendaView({
  periodKey,
  onPeriodKey,
  customStart,
  customEnd,
  onCustomStart,
  onCustomEnd,
  slots,
  loading,
  onEdit,
  onDelete,
}: {
  periodKey:     PeriodKey
  onPeriodKey:   (k: PeriodKey) => void
  customStart:   string
  customEnd:     string
  onCustomStart: (v: string) => void
  onCustomEnd:   (v: string) => void
  slots:         SlotRow[]
  loading:       boolean
  onEdit:        (s: SlotRow) => void
  onDelete:      (s: SlotRow) => void
}) {
  const [selectedDay, setSelectedDay] = useState<string | null>(null)

  const today = new Date()
  const [start, end] = periodKey === 'custom'
    ? [customStart ? new Date(customStart) : today, customEnd ? new Date(customEnd) : addDays(today, 7)]
    : computePeriod(periodKey, today)

  const days: Date[] = []
  const cursor = new Date(start)
  while (cursor <= end) {
    days.push(new Date(cursor))
    cursor.setDate(cursor.getDate() + 1)
  }

  const byDay = new Map<string, SlotRow[]>()
  for (const s of slots) {
    const key = s.date
    if (!byDay.has(key)) byDay.set(key, [])
    byDay.get(key)!.push(s)
  }

  const selectedSlots = selectedDay ? (byDay.get(selectedDay) ?? []) : []
  const selectedLabel = selectedDay
    ? (() => { const d = new Date(selectedDay + 'T00:00:00'); return `${DAY_SHORT[d.getDay()]} ${d.getDate()}` })()
    : ''

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-1.5">
        {PERIOD_LABELS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => onPeriodKey(key)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              periodKey === key
                ? 'bg-brand-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {periodKey === 'custom' && (
        <div className="flex items-center gap-3">
          <input
            type="date"
            value={customStart}
            onChange={(e) => onCustomStart(e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
          />
          <span className="text-gray-400 text-sm">to</span>
          <input
            type="date"
            value={customEnd}
            onChange={(e) => onCustomEnd(e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
          />
        </div>
      )}

      {loading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : (
        <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(7, minmax(0, 1fr))' }}>
          {days.map((d) => {
            const key     = isoDate(d)
            const daySlots = byDay.get(key) ?? []
            const label   = `${DAY_SHORT[d.getDay()]} ${d.getDate()}`
            const isToday = isoDate(d) === isoDate(today)
            return (
              <div
                key={key}
                onClick={() => setSelectedDay(key)}
                className={`rounded-xl border cursor-pointer p-2 min-h-[90px] hover:border-brand-300 transition-colors ${
                  isToday ? 'border-brand-400 bg-brand-50/40' : 'border-gray-100 bg-white'
                }`}
              >
                <p className={`text-xs font-semibold mb-1.5 ${isToday ? 'text-brand-600' : 'text-gray-500'}`}>
                  {label}
                </p>
                {daySlots.length === 0 ? (
                  <p className="text-gray-300 text-xs">—</p>
                ) : (
                  <div className="space-y-1">
                    {daySlots.map((s) => (
                      <div key={s.uuid} className="flex items-center gap-1 text-xs">
                        <TypeBadge type={s.type} />
                        <span className="text-gray-500 truncate">{s.department}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {selectedDay && (
        <DaySlideOver
          dayLabel={selectedLabel}
          slots={selectedSlots}
          onClose={() => setSelectedDay(null)}
          onEdit={(s) => { setSelectedDay(null); onEdit(s) }}
          onDelete={(s) => { setSelectedDay(null); onDelete(s) }}
        />
      )}
    </div>
  )
}

// ── Delete confirmation dialog ────────────────────────────────────────────────

function DeleteConfirmDialog({
  slot,
  onCancel,
  onConfirm,
  deleting,
}: {
  slot:      SlotRow
  onCancel:  () => void
  onConfirm: () => void
  deleting:  boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-6 space-y-4">
        <h3 className="text-base font-semibold text-gray-900">Delete slot?</h3>
        <p className="text-sm text-gray-600">
          This action cannot be undone. The slot on <strong>{slot.date}</strong> ({slot.type} / {slot.department}) will be permanently removed.
        </p>
        {slot.mediciner_crm && (
          <p className="text-sm text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
            This slot is currently assigned to {slot.mediciner_crm}.
          </p>
        )}
        <div className="flex justify-end gap-3 pt-2">
          <button onClick={onCancel} className="btn-ghost text-gray-600 border border-gray-200">Cancel</button>
          <button onClick={onConfirm} disabled={deleting} className="btn-brand bg-red-600 hover:bg-red-700">
            {deleting ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function SlotManagement() {
  const today = new Date()

  // view toggle
  const [view, setView] = useState<'table' | 'agenda'>('table')

  // table state
  const TABLE_WINDOW = 30
  const [tableFrom, setTableFrom] = useState<Date>(addDays(today, -TABLE_WINDOW))
  const [tableTo,   setTableTo]   = useState<Date>(addDays(today, 60))
  const [page,      setPage]      = useState(1)
  const PER_PAGE = 20

  // agenda state
  const [periodKey,    setPeriodKey]    = useState<PeriodKey>('week')
  const [customStart,  setCustomStart]  = useState('')
  const [customEnd,    setCustomEnd]    = useState('')

  // data state
  const [slots,   setSlots]   = useState<SlotRow[]>([])
  const [total,   setTotal]   = useState(0)
  const [pages,   setPages]   = useState(1)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  // modals
  const [showCreate,    setShowCreate]    = useState(false)
  const [editSlot,      setEditSlot]      = useState<SlotRow | null>(null)
  const [deleteTarget,  setDeleteTarget]  = useState<SlotRow | null>(null)
  const [deleting,      setDeleting]      = useState(false)

  // ── Fetch ──────────────────────────────────────────────────────────────────

  const fetchTableSlots = useCallback(async (from: Date, to: Date, p: number) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({
        from_date: isoDate(from),
        to_date:   isoDate(to),
        page:      String(p),
        per_page:  String(PER_PAGE),
      })
      const data = await api.get<SlotsPage>(`/slots?${params}`)
      setSlots(data.items)
      setTotal(data.total)
      setPages(data.pages)
    } catch {
      setError('Failed to load slots.')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchAgendaSlots = useCallback(async (from: Date, to: Date) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({
        from_date: isoDate(from),
        to_date:   isoDate(to),
        per_page:  '500',
      })
      const data = await api.get<SlotsPage>(`/slots?${params}`)
      setSlots(data.items)
      setTotal(data.total)
      setPages(1)
    } catch {
      setError('Failed to load slots.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (view === 'table') {
      fetchTableSlots(tableFrom, tableTo, page)
    } else {
      const [from, to] = periodKey === 'custom'
        ? [
            customStart ? new Date(customStart) : today,
            customEnd   ? new Date(customEnd)   : addDays(today, 7),
          ]
        : computePeriod(periodKey, today)
      fetchAgendaSlots(from, to)
    }
  }, [view, tableFrom, tableTo, page, periodKey, customStart, customEnd, fetchTableSlots, fetchAgendaSlots])

  // ── Table navigation ───────────────────────────────────────────────────────

  function shiftWindow(days: number) {
    setTableFrom((d) => addDays(d, days))
    setTableTo((d)   => addDays(d, days))
    setPage(1)
  }

  function jumpToToday() {
    setTableFrom(addDays(today, -TABLE_WINDOW))
    setTableTo(addDays(today, 60))
    setPage(1)
  }

  // ── Slot mutations ─────────────────────────────────────────────────────────

  function handleCreated(slot: SlotRow) {
    setShowCreate(false)
    setSlots((prev) => [slot, ...prev])
    setTotal((n) => n + 1)
  }

  function handleSaved(updated: SlotRow) {
    setEditSlot(null)
    setSlots((prev) => prev.map((s) => s.uuid === updated.uuid ? updated : s))
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await api.delete(`/slots/${deleteTarget.uuid}`)
      setSlots((prev) => prev.filter((s) => s.uuid !== deleteTarget.uuid))
      setTotal((n) => n - 1)
      setDeleteTarget(null)
    } catch {
      // leave dialog open; user can retry
    } finally {
      setDeleting(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full">
      <Header title="Slots" subtitle="Manage shift slots" />

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">

        {/* Top bar: toggle + create */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-1">
            {(['table', 'agenda'] as const).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors capitalize ${
                  view === v
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {v.charAt(0).toUpperCase() + v.slice(1)}
              </button>
            ))}
          </div>
          <button className="btn-brand" onClick={() => setShowCreate(true)}>
            + New Slot
          </button>
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        {view === 'table' ? (
          <TableView
            page={page}
            perPage={PER_PAGE}
            fromDate={tableFrom}
            toDate={tableTo}
            onPrev={() => shiftWindow(-TABLE_WINDOW)}
            onNext={() => shiftWindow(TABLE_WINDOW)}
            onToday={jumpToToday}
            onSetFrom={setTableFrom}
            onSetTo={setTableTo}
            onEdit={setEditSlot}
            onDelete={setDeleteTarget}
            onPageChange={setPage}
            slots={slots}
            total={total}
            pages={pages}
            loading={loading}
          />
        ) : (
          <AgendaView
            periodKey={periodKey}
            onPeriodKey={(k) => { setPeriodKey(k); setPage(1) }}
            customStart={customStart}
            customEnd={customEnd}
            onCustomStart={setCustomStart}
            onCustomEnd={setCustomEnd}
            slots={slots}
            loading={loading}
            onEdit={setEditSlot}
            onDelete={setDeleteTarget}
          />
        )}
      </div>

      {showCreate && (
        <CreateSlotModal
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}

      {editSlot && (
        <EditSlotModal
          slot={editSlot}
          onClose={() => setEditSlot(null)}
          onSaved={handleSaved}
        />
      )}

      {deleteTarget && (
        <DeleteConfirmDialog
          slot={deleteTarget}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDeleteConfirm}
          deleting={deleting}
        />
      )}
    </div>
  )
}

import { useState, useEffect, FormEvent } from 'react'
import { api } from '@/shared/api'
import { useAuth } from '@/shared/context/AuthContext'
import {
  maskTaxId, taxIdError, taxIdLabel, taxIdPlaceholder, stripCNPJ,
} from '@/shared/taxId'
import type { HospitalRow } from '@/modules/crud/hospitals/HospitalManagement'
import { CreateHospitalOverlay } from '@/modules/crud/hospitals/CreateHospitalOverlay'

interface Props {
  onClose:     () => void
  onCreated:   () => void
  initialData?: {
    name:      string
    email:     string
    telephone: string
    role:      string
  }
}

const ROLES = ['SA-root', 'Scheduler', 'Mediciner'] as const

type HospitalMode = 'taxid' | 'name'

// ── Segmented control button ────────────────────────────────────────────────

function SegBtn({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 py-1.5 text-xs font-medium transition-colors ${
        active
          ? 'bg-brand-600 text-white'
          : 'bg-white text-gray-500 hover:bg-gray-50'
      }`}
    >
      {label}
    </button>
  )
}

// ── Confirmed hospital chip ─────────────────────────────────────────────────

function HospitalChip({
  hospital, country, onClear,
}: { hospital: HospitalRow; country: string; onClear: () => void }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-green-200 bg-green-50 px-3 py-2">
      <div>
        <p className="text-sm font-medium text-gray-900">{hospital.name}</p>
        <p className="font-mono text-xs text-gray-500">{maskTaxId(country, hospital.cnpj)}</p>
      </div>
      <button type="button" onClick={onClear} className="ml-3 text-xs text-gray-400 hover:text-red-500">✕</button>
    </div>
  )
}

// ── Main component ──────────────────────────────────────────────────────────

export function CreateSAModal({ onClose, onCreated, initialData }: Props) {
  const { country } = useAuth()

  const [form, setForm] = useState({
    name:      initialData?.name      ?? '',
    telephone: initialData?.telephone ?? '',
    email:     initialData?.email     ?? '',
    role:      initialData?.role      ?? 'SA-root',
  })

  // Hospital state (Scheduler only)
  const [hospitals,    setHospitals]    = useState<HospitalRow[]>([])
  const [hospMode,     setHospMode]     = useState<HospitalMode>('taxid')
  const [confirmed,    setConfirmed]    = useState<HospitalRow | null>(null)
  const [showOverlay,  setShowOverlay]  = useState(false)

  // Tax-ID search state
  const [taxIdInput, setTaxIdInput] = useState('')
  const [taxIdErr,   setTaxIdErr]   = useState<string | null>(null)

  // Name search state
  const [nameSearch, setNameSearch] = useState('')

  const [error,   setError]   = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const isScheduler = form.role === 'Scheduler'

  useEffect(() => {
    if (!isScheduler) return
    api.get<HospitalRow[]>('/hospitals')
      .then(setHospitals)
      .catch(() => setHospitals([]))
  }, [isScheduler])

  function setField(k: string, v: string) {
    setForm((f) => ({ ...f, [k]: v }))
  }

  function switchMode(m: HospitalMode) {
    setHospMode(m)
    setConfirmed(null)
    setTaxIdInput('')
    setTaxIdErr(null)
    setNameSearch('')
  }

  // Tax-ID search: hospital matching the typed CNPJ
  const taxIdClean = stripCNPJ(taxIdInput)
  const taxIdMatch = taxIdClean.length === 14
    ? hospitals.find((h) => h.cnpj.toUpperCase() === taxIdClean)
    : undefined

  // Name search: substring filter
  const nameMatches = nameSearch.trim().length >= 2
    ? hospitals.filter((h) => h.name.toLowerCase().includes(nameSearch.toLowerCase()))
    : []

  function hospitalValid(): boolean {
    if (!isScheduler) return true
    return confirmed !== null
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!hospitalValid()) {
      setError('Please select or create a Hospital.')
      return
    }
    setError(null)
    setLoading(true)

    try {
      await api.post('/users', {
        ...form,
        ...(isScheduler && confirmed && { hospitalUuid: confirmed.uuid }),
      })
      onCreated()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
        <div className="card w-full max-w-md p-6 shadow-xl max-h-[90vh] overflow-y-auto">
          <h2 className="mb-4 text-base font-semibold text-gray-900">
            {initialData ? 'Reinvite User' : 'Invite New User'}
          </h2>

          <form onSubmit={submit} className="space-y-3">
            <Field label="Full name"  type="text"  value={form.name}      onChange={(v) => setField('name', v)} />
            <Field label="Email"      type="email" value={form.email}     onChange={(v) => setField('email', v)} />
            <Field label="Telephone"  type="tel"   value={form.telephone} onChange={(v) => setField('telephone', v)} placeholder="+5511999999999" />

            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Role</label>
              <select
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                value={form.role}
                onChange={(e) => { setField('role', e.target.value); setConfirmed(null) }}
              >
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>

            {/* ── Hospital section (Scheduler only) ─────────────────────── */}
            {isScheduler && (
              <div className="rounded-lg border border-gray-200 p-3 space-y-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Hospital</p>

                {/* Confirmed chip */}
                {confirmed ? (
                  <HospitalChip hospital={confirmed} country={country} onClear={() => setConfirmed(null)} />
                ) : (
                  <>
                    {/* Search mode toggle */}
                    <div className="flex divide-x divide-gray-200 overflow-hidden rounded-md border border-gray-200">
                      <SegBtn label={taxIdLabel(country)} active={hospMode === 'taxid'} onClick={() => switchMode('taxid')} />
                      <SegBtn label="Name"                active={hospMode === 'name'}  onClick={() => switchMode('name')}  />
                    </div>

                    {/* Tax ID search */}
                    {hospMode === 'taxid' && (
                      <div>
                        <input
                          type="text"
                          autoCapitalize="characters"
                          autoCorrect="off"
                          spellCheck={false}
                          className="w-full rounded-md border border-gray-200 px-3 py-2 font-mono text-sm text-gray-900 placeholder-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                          placeholder={taxIdPlaceholder(country)}
                          value={taxIdInput}
                          onChange={(e) => { setTaxIdInput(maskTaxId(country, e.target.value)); setTaxIdErr(null) }}
                          onBlur={() => setTaxIdErr(taxIdError(country, taxIdInput))}
                        />
                        {taxIdErr && <p className="mt-1 text-xs text-red-600">{taxIdErr}</p>}
                        {taxIdClean.length === 14 && !taxIdErr && (
                          taxIdMatch ? (
                            <div className="mt-2 flex items-center justify-between rounded bg-gray-50 px-3 py-2 text-sm">
                              <span className="font-medium text-gray-800">{taxIdMatch.name}</span>
                              <button
                                type="button"
                                className="text-xs font-medium text-brand-600 hover:underline"
                                onClick={() => setConfirmed(taxIdMatch)}
                              >
                                Select
                              </button>
                            </div>
                          ) : (
                            <p className="mt-1 text-xs text-amber-600">Not found — create it below.</p>
                          )
                        )}
                      </div>
                    )}

                    {/* Name search */}
                    {hospMode === 'name' && (
                      <div>
                        <input
                          type="text"
                          className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                          placeholder="Type hospital name…"
                          value={nameSearch}
                          onChange={(e) => setNameSearch(e.target.value)}
                        />
                        {nameMatches.length > 0 && (
                          <div className="mt-1 max-h-40 divide-y divide-gray-100 overflow-y-auto rounded-md border border-gray-200">
                            {nameMatches.map((h) => (
                              <div key={h.uuid} className="flex items-center justify-between px-3 py-2 hover:bg-gray-50">
                                <div>
                                  <p className="text-sm font-medium text-gray-800">{h.name}</p>
                                  <p className="font-mono text-xs text-gray-400">{maskTaxId(country, h.cnpj)}</p>
                                </div>
                                <button
                                  type="button"
                                  className="text-xs font-medium text-brand-600 hover:underline"
                                  onClick={() => setConfirmed(h)}
                                >
                                  Select
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                        {nameSearch.trim().length >= 2 && nameMatches.length === 0 && (
                          <p className="mt-1 text-xs text-amber-600">No hospitals found — create it below.</p>
                        )}
                      </div>
                    )}

                    {/* Create new hospital */}
                    <button
                      type="button"
                      className="w-full rounded-md border border-dashed border-gray-300 py-2 text-xs font-medium text-gray-500 hover:border-brand-400 hover:text-brand-600 transition-colors"
                      onClick={() => setShowOverlay(true)}
                    >
                      + Create new hospital
                    </button>
                  </>
                )}
              </div>
            )}

            {error && <p className="text-xs text-red-600">{error}</p>}

            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="btn-ghost" onClick={onClose} disabled={loading}>Cancel</button>
              <button
                type="submit"
                className="btn-brand"
                disabled={loading || (isScheduler && !hospitalValid())}
              >
                {loading ? 'Sending…' : 'Send Invitation'}
              </button>
            </div>
          </form>
        </div>
      </div>

      {showOverlay && (
        <CreateHospitalOverlay
          onClose={() => setShowOverlay(false)}
          onCreated={(h) => { setConfirmed(h); setShowOverlay(false) }}
        />
      )}
    </>
  )
}

function Field({ label, type, value, onChange, placeholder }: {
  label: string; type: string; value: string
  onChange: (v: string) => void; placeholder?: string
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-600">{label}</label>
      <input
        type={type}
        className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required
      />
    </div>
  )
}

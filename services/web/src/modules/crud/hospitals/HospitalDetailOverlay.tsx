import { useEffect, useState, useRef, FormEvent } from 'react'
import { api } from '@/shared/api'
import { useAuth } from '@/shared/context/AuthContext'
import { maskTaxId, maskZip, zipPlaceholder } from '@/shared/taxId'
import type { HospitalRow } from './HospitalManagement'

const SLOT_TYPES = ['UTI', 'PS', 'PA', 'CC', 'ENF'] as const
type SlotType = typeof SLOT_TYPES[number]

const SLOT_LABELS: Record<SlotType, string> = {
  UTI: 'Unidade de Terapia Intensiva',
  PS:  'Pronto-Socorro',
  PA:  'Pronto-Atendimento',
  CC:  'Centro Cirúrgico',
  ENF: 'Enfermaria',
}

const STATUS_CLASSES: Record<string, string> = {
  active:   'bg-green-50 text-green-700 ring-1 ring-inset ring-green-200',
  inactive: 'bg-yellow-50 text-yellow-700 ring-1 ring-inset ring-yellow-200',
  disabled: 'bg-red-50 text-red-700 ring-1 ring-inset ring-red-200',
}

function extractCep(address: string): string {
  const m = address.match(/\d{5}-\d{3}/)
  return m ? m[0] : ''
}

async function lookupCep(cep: string): Promise<string | null> {
  const clean = cep.replace(/\D/g, '')
  if (clean.length !== 8) return null
  try {
    const res  = await fetch(`https://viacep.com.br/ws/${clean}/json/`)
    const data = await res.json()
    if (data.erro) return null
    const parts: string[] = []
    if (data.bairro) parts.push(`- ${data.bairro} -`)
    parts.push(`${data.localidade} - ${data.uf}`)
    return data.logradouro
      ? `${data.logradouro}, ${parts.join(', ')}, CEP ${data.cep}`
      : `${parts.join(', ')}, CEP ${data.cep}`
  } catch {
    return null
  }
}

interface Props {
  uuid:    string
  onClose: () => void
  onSaved: (hospital: HospitalRow) => void
}

export function HospitalDetailOverlay({ uuid, onClose, onSaved }: Props) {
  const { country } = useAuth()

  const [hospital,  setHospital]  = useState<HospitalRow | null>(null)
  const [loading,   setLoading]   = useState(true)
  const [fetchErr,  setFetchErr]  = useState<string | null>(null)
  const [editing,   setEditing]   = useState(false)
  const [name,      setName]      = useState('')
  const [address,   setAddress]   = useState('')
  const [cep,       setCep]       = useState('')
  const [cepBusy,   setCepBusy]   = useState(false)
  const [cepErr,    setCepErr]    = useState<string | null>(null)
  const [slotTypes, setSlotTypes] = useState<string[]>([])
  const [saving,    setSaving]    = useState(false)
  const [saveErr,   setSaveErr]   = useState<string | null>(null)

  const addressRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setLoading(true)
    api.get<HospitalRow>(`/hospitals/${uuid}`)
      .then((h) => { setHospital(h); resetForm(h) })
      .catch(() => setFetchErr('Hospital not found.'))
      .finally(() => setLoading(false))
  }, [uuid])

  function resetForm(h: HospitalRow) {
    setName(h.name)
    setAddress(h.address)
    setCep(extractCep(h.address))
    setSlotTypes(h.slotTypes)
    setSaveErr(null)
    setCepErr(null)
  }

  function startEdit() { if (hospital) resetForm(hospital); setEditing(true) }
  function cancelEdit() { if (hospital) resetForm(hospital); setEditing(false) }

  async function handleCepSearch() {
    setCepBusy(true); setCepErr(null)
    const result = await lookupCep(cep)
    setCepBusy(false)
    if (result) {
      setAddress(result)
      const cursorPos = result.indexOf(',') + 2
      setTimeout(() => { addressRef.current?.focus(); addressRef.current?.setSelectionRange(cursorPos, cursorPos) }, 0)
    } else {
      setCepErr('CEP not found')
    }
  }

  function toggleSlot(s: string) {
    setSlotTypes((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s])
  }

  async function save(e: FormEvent) {
    e.preventDefault()
    if (!editing) return
    setSaving(true); setSaveErr(null)
    try {
      const updated = await api.put<HospitalRow>(`/hospitals/${uuid}`, {
        name: name.trim(), address: address.trim(), slotTypes,
      })
      setHospital(updated); onSaved(updated); setEditing(false)
    } catch (err: unknown) {
      setSaveErr(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const status = hospital?.status ?? 'active'

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
      <div className="card w-[68vw] p-6 shadow-2xl max-h-[90vh] overflow-y-auto">

        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-gray-900">Hospital</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">✕</button>
        </div>

        {loading  && <p className="py-8 text-center text-sm text-gray-400">Loading…</p>}
        {fetchErr && <p className="text-sm text-red-600">{fetchErr}</p>}

        {!loading && hospital && (
          <form onSubmit={save} className="space-y-5">

            {/* Line 1: CNPJ · Name · Status */}
            <div className="flex items-center gap-3">
              <span className="flex-shrink-0 font-mono text-sm text-gray-500">
                {maskTaxId(country, hospital.cnpj)}
              </span>
              <span className="flex-shrink-0 text-gray-200" aria-hidden>·</span>
              {editing ? (
                <input
                  type="text"
                  className="flex-1 rounded-md border border-gray-200 px-3 py-1.5 text-sm font-semibold text-gray-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              ) : (
                <span className="flex-1 font-semibold text-gray-900">{hospital.name}</span>
              )}
              <span className={`flex-shrink-0 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_CLASSES[status]}`}>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </span>
            </div>

            {/* Line 2: Address — CEP + address cols when editing, pin + text when viewing */}
            {editing ? (
              <div className="flex gap-4 items-start">
                <div className="w-44 flex-shrink-0">
                  <label className="mb-1 block text-xs font-medium text-gray-600">CEP (ZIP Code)</label>
                  <div className="flex items-center gap-1">
                    <input
                      type="text"
                      placeholder={zipPlaceholder(country)}
                      className="min-w-0 flex-1 rounded-md border border-gray-200 px-3 py-2 text-sm text-right text-gray-900 placeholder-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                      value={cep}
                      onChange={(e) => { setCep(maskZip(country, e.target.value)); setCepErr(null) }}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleCepSearch() } }}
                    />
                    <button
                      type="button"
                      title="Search Brazilian CEP"
                      className="flex h-[38px] w-9 flex-shrink-0 items-center justify-center rounded-md bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40"
                      onClick={handleCepSearch}
                      disabled={cepBusy}
                    >
                      <span className="text-sm font-bold">{cepBusy ? '…' : '->'}</span>
                    </button>
                  </div>
                  {cepErr && <p className="mt-1 text-xs text-red-600">{cepErr}</p>}
                </div>
                <div className="flex-1">
                  <label className="mb-1 block text-xs font-medium text-gray-600">Address</label>
                  <input
                    ref={addressRef}
                    type="text"
                    className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="Rua das Flores, 100, - Centro -, São Paulo - SP, CEP 01310-100"
                    required
                  />
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-2 text-sm text-gray-700">
                <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-gray-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
                  <path fillRule="evenodd" d="M9.69 18.933l.003.001C9.89 19.02 10 19 10 19s.11.02.308-.066l.002-.001.006-.003.018-.008a5.741 5.741 0 00.281-.14c.186-.096.446-.24.757-.433.62-.384 1.445-.966 2.274-1.765C15.302 14.988 17 12.493 17 9A7 7 0 103 9c0 3.492 1.698 5.988 3.355 7.584a13.731 13.731 0 002.273 1.765 11.842 11.842 0 00.976.544l.062.029.018.008.006.003zM10 11.25a2.25 2.25 0 100-4.5 2.25 2.25 0 000 4.5z" clipRule="evenodd" />
                </svg>
                <span>{hospital.address || <span className="text-gray-400">No address set</span>}</span>
              </div>
            )}

            {/* Line 3: Allowed Slots — checkboxes when editing, badges when viewing */}
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">Allowed Slots</p>
              {editing ? (
                <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                  <label className="col-span-2 flex cursor-pointer items-center gap-2">
                    <input type="checkbox" className="accent-brand-600" checked={slotTypes.includes('UTI')} onChange={() => toggleSlot('UTI')} />
                    <span className="inline-flex w-10 items-center justify-center rounded px-1.5 py-0.5 text-xs font-semibold bg-brand-50 text-brand-700">UTI</span>
                    <span className="text-sm text-gray-600">{SLOT_LABELS.UTI}</span>
                  </label>
                  {(['PS', 'PA', 'CC', 'ENF'] as SlotType[]).map((s) => (
                    <label key={s} className="flex cursor-pointer items-center gap-2">
                      <input type="checkbox" className="accent-brand-600" checked={slotTypes.includes(s)} onChange={() => toggleSlot(s)} />
                      <span className="inline-flex w-10 items-center justify-center rounded px-1.5 py-0.5 text-xs font-semibold bg-brand-50 text-brand-700">{s}</span>
                      <span className="text-sm text-gray-600">{SLOT_LABELS[s]}</span>
                    </label>
                  ))}
                </div>
              ) : hospital.slotTypes.length === 0 ? (
                <span className="text-sm text-gray-400">None configured</span>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {hospital.slotTypes.map((s) => (
                    <div key={s} className="flex items-center gap-2.5">
                      <span className="inline-flex w-10 items-center justify-center rounded px-1.5 py-0.5 text-xs font-semibold bg-brand-50 text-brand-700">{s}</span>
                      <span className="text-sm text-gray-600">{SLOT_LABELS[s as SlotType] ?? s}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Line 4: Summary */}
            <div className="border-t border-gray-100 pt-4">
              <p className="mb-3 text-xs font-medium uppercase tracking-wide text-gray-400">Summary</p>
              <div className="grid grid-cols-3 gap-4">
                <SummaryLink label="Schedulers" value={hospital.schedulerCount} />
                <SummaryLink label="Mediciners" value="—" />
                <SummaryLink label="Slots" value="—" subtitle="agenda" />
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-100">
              {saveErr && <p className="mr-auto text-xs text-red-600">{saveErr}</p>}
              {editing ? (
                <>
                  <button type="button" className="btn-ghost" onClick={cancelEdit} disabled={saving}>Cancel</button>
                  <button type="submit" className="btn-brand" disabled={saving}>
                    {saving ? 'Saving…' : 'Save changes'}
                  </button>
                </>
              ) : (
                <button type="button" className="btn-brand" onClick={startEdit}>Edit</button>
              )}
            </div>

          </form>
        )}

      </div>
    </div>
  )
}

function SummaryLink({
  label, value, subtitle,
}: { label: string; value: string | number; subtitle?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
        {label}
        {subtitle && <span className="ml-1 normal-case font-normal text-gray-300">· {subtitle}</span>}
      </p>
      <p className="text-2xl font-normal tabular-nums text-gray-700">{value}</p>
      <span className="text-xs text-gray-300 cursor-not-allowed select-none">View list →</span>
    </div>
  )
}

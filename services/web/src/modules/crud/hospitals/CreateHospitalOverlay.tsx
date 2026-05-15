import { useState, useRef, FormEvent } from 'react'
import { api } from '@/shared/api'
import { useAuth } from '@/shared/context/AuthContext'
import { maskTaxId, taxIdError, taxIdLabel, taxIdPlaceholder, stripCNPJ, maskZip, zipPlaceholder } from '@/shared/taxId'
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

interface Props {
  onClose:   () => void
  onCreated: (hospital: HospitalRow) => void
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

export function CreateHospitalOverlay({ onClose, onCreated }: Props) {
  const { country } = useAuth()

  const addressRef = useRef<HTMLTextAreaElement>(null)

  const [cnpj,      setCnpj]      = useState('')
  const [cnpjErr,   setCnpjErr]   = useState<string | null>(null)
  const [name,      setName]      = useState('')
  const [address,   setAddress]   = useState('')
  const [cep,       setCep]       = useState('')
  const [cepBusy,   setCepBusy]   = useState(false)
  const [cepErr,    setCepErr]    = useState<string | null>(null)
  const [slotTypes, setSlotTypes] = useState<string[]>([])
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState<string | null>(null)

  function toggleSlot(s: string) {
    setSlotTypes((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    )
  }

  async function handleCepSearch() {
    setCepBusy(true)
    setCepErr(null)
    const result = await lookupCep(cep)
    setCepBusy(false)
    if (result) {
      setAddress(result)
      const cursorPos = result.indexOf(',') + 2
      setTimeout(() => {
        addressRef.current?.focus()
        addressRef.current?.setSelectionRange(cursorPos, cursorPos)
      }, 0)
    } else {
      setCepErr('CEP not found')
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    const clean = stripCNPJ(cnpj)
    const err   = taxIdError(country, cnpj)
    if (err) { setCnpjErr(err); return }
    if (!name.trim() || !address.trim()) { setError('All fields are required.'); return }

    setError(null)
    setLoading(true)
    try {
      const hospital = await api.post<HospitalRow>('/hospitals', {
        cnpj:      clean,
        name:      name.trim(),
        address:   address.trim(),
        slotTypes,
      })
      onCreated(hospital)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
      <div className="card w-[68vw] p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-gray-900">New Hospital</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">✕</button>
        </div>

        <form onSubmit={submit} className="space-y-4">

          {/* Row 1: CNPJ (fixed, narrower) | Name (takes remaining width) */}
          <div className="flex gap-4">
            <div className="w-44 flex-shrink-0">
              <label className="mb-1 block text-xs font-medium text-gray-600">{taxIdLabel(country)}</label>
              <input
                type="text"
                autoCapitalize="characters"
                autoCorrect="off"
                spellCheck={false}
                className="w-full rounded-md border border-gray-200 px-3 py-2 font-mono text-sm text-right text-gray-900 placeholder-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder={taxIdPlaceholder(country)}
                value={cnpj}
                onChange={(e) => { setCnpj(maskTaxId(country, e.target.value)); setCnpjErr(null) }}
                onBlur={() => setCnpjErr(taxIdError(country, cnpj))}
                required
              />
              {cnpjErr && <p className="mt-1 text-xs text-red-600">{cnpjErr}</p>}
            </div>

            <div className="flex-1">
              <label className="mb-1 block text-xs font-medium text-gray-600">Name</label>
              <input
                type="text"
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm text-left text-gray-900 placeholder-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder="Hospital Central"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Row 2: CEP + inline search button (aligned with CNPJ col) | Address */}
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
              <textarea
                ref={addressRef}
                rows={2}
                className="w-full resize-none rounded-md border border-gray-200 px-3 py-2 text-sm text-left text-gray-900 placeholder-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder="Rua das Flores, 100,  Centro, São Paulo - SP, CEP 01310-100"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Row 3: Slot types — UTI full-width, then pairs */}
          <div>
            <p className="mb-2 text-xs font-medium text-gray-600">Allowed slot types</p>
            <div className="grid grid-cols-2 gap-x-6 gap-y-2">
              {/* UTI spans both columns */}
              <label className="col-span-2 flex cursor-pointer items-center gap-2">
                <input type="checkbox" className="accent-brand-600" checked={slotTypes.includes('UTI')} onChange={() => toggleSlot('UTI')} />
                <span className="inline-flex w-10 items-center justify-center rounded px-1.5 py-0.5 text-xs font-semibold bg-brand-50 text-brand-700">UTI</span>
                <span className="text-sm text-gray-600">{SLOT_LABELS.UTI}</span>
              </label>
              {/* Remaining 4 in 2-column pairs: PS|PA, CC|ENF */}
              {(['PS', 'PA', 'CC', 'ENF'] as SlotType[]).map((s) => (
                <label key={s} className="flex cursor-pointer items-center gap-2">
                  <input type="checkbox" className="accent-brand-600" checked={slotTypes.includes(s)} onChange={() => toggleSlot(s)} />
                  <span className="inline-flex w-10 items-center justify-center rounded px-1.5 py-0.5 text-xs font-semibold bg-brand-50 text-brand-700">{s}</span>
                  <span className="text-sm text-gray-600">{SLOT_LABELS[s]}</span>
                </label>
              ))}
            </div>
          </div>

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
            <button type="button" className="btn-ghost" onClick={onClose} disabled={loading}>Cancel</button>
            <button type="submit" className="btn-brand" disabled={loading}>
              {loading ? 'Creating…' : 'Create Hospital'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

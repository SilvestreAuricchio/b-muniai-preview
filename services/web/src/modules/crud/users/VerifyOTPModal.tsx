import { useState, FormEvent } from 'react'
import { api } from '@/shared/api'

interface Props {
  uuid:        string
  devOtp:      string   // prefilled from _dev field (channel = None)
  onClose:     () => void
  onActivated: () => void
}

export function VerifyOTPModal({ uuid, devOtp, onClose, onActivated }: Props) {
  const [otp,     setOtp]     = useState(devOtp)
  const [error,   setError]   = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await api.post(`/users/${uuid}/verify`, { otp })
      onActivated()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Verification failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="card w-full max-w-sm p-6 shadow-xl">
        <h2 className="mb-1 text-base font-semibold text-gray-900">Verify OTP</h2>
        <p className="mb-4 text-xs text-gray-500">
          Enter the 6-digit code sent to the user.{' '}
          {devOtp && <span className="font-mono text-yellow-700">[DEV: {devOtp}]</span>}
        </p>

        <form onSubmit={submit} className="space-y-3">
          <input
            type="text"
            inputMode="numeric"
            pattern="\d{6}"
            maxLength={6}
            placeholder="000000"
            className="w-full rounded-md border border-gray-200 px-3 py-2 text-center font-mono text-2xl tracking-widest text-gray-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
            required
          />

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" className="btn-ghost" onClick={onClose} disabled={loading}>Cancel</button>
            <button type="submit" className="btn-brand" disabled={loading || otp.length < 6}>
              {loading ? 'Verifying…' : 'Activate'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

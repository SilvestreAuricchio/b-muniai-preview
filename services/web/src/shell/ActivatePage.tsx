import { useState, useEffect, FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { RedCross } from '@/shared/components/RedCross'

type Phase = 'input' | 'success' | 'already_done' | 'error'

export function ActivatePage() {
  const { uuid } = useParams<{ uuid: string }>()
  const [otp,     setOtp]     = useState('')
  const [phase,   setPhase]   = useState<Phase>('input')
  const [errMsg,  setErrMsg]  = useState('')
  const [loading, setLoading] = useState(false)

  // Auto-fill OTP from ?otp= query param (magic link support)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const q = params.get('otp')
    if (q && /^\d{6}$/.test(q)) setOtp(q)
  }, [])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setErrMsg('')
    try {
      const res = await fetch(`/bff/users/${uuid}/verify`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ otp }),
      })
      const data = await res.json()
      if (res.status === 422) {
        setErrMsg(data.error ?? 'Invalid or expired code. Check the code and try again.')
      } else if (res.status === 409) {
        setPhase('already_done')
      } else if (!res.ok) {
        setErrMsg(data.error ?? 'Something went wrong. Please try again.')
      } else {
        setPhase('success')
      }
    } catch {
      setErrMsg('Could not reach the server. Check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">

        {/* Brand */}
        <div className="text-center space-y-2">
          <div className="flex justify-center text-brand-600">
            <RedCross size={52} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            Muni<span className="text-brand-600">AI</span>
          </h1>
          <p className="text-sm text-gray-500">Medical staffing platform</p>
        </div>

        {/* Card */}
        <div className="card p-8 space-y-5">

          {phase === 'input' && (
            <>
              <div className="space-y-1">
                <h2 className="text-base font-semibold text-gray-900">Activate your account</h2>
                <p className="text-sm text-gray-500">
                  Enter the 6-digit code from your invitation email.
                </p>
              </div>

              <form onSubmit={submit} className="space-y-4">
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="\d{6}"
                  maxLength={6}
                  placeholder="000000"
                  autoFocus
                  className="w-full rounded-md border border-gray-200 px-3 py-3 text-center font-mono text-3xl tracking-[0.5em] text-gray-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  required
                />

                {errMsg && (
                  <p className="text-xs text-red-600">{errMsg}</p>
                )}

                <button
                  type="submit"
                  className="btn-brand w-full py-3"
                  disabled={loading || otp.length < 6}
                >
                  {loading ? 'Verifying…' : 'Activate account'}
                </button>
              </form>
            </>
          )}

          {phase === 'success' && (
            <div className="space-y-3 text-center">
              <div className="flex justify-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100 text-green-600 text-2xl">✓</span>
              </div>
              <h2 className="text-base font-semibold text-gray-900">Code verified!</h2>
              <p className="text-sm text-gray-500">
                Your identity has been confirmed. An administrator will review and activate your
                account shortly. You will be notified by email.
              </p>
            </div>
          )}

          {phase === 'already_done' && (
            <div className="space-y-3 text-center">
              <div className="flex justify-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-blue-600 text-2xl">ℹ</span>
              </div>
              <h2 className="text-base font-semibold text-gray-900">Already verified</h2>
              <p className="text-sm text-gray-500">
                This invitation code has already been used. If your account is not yet active,
                please wait for administrator approval.
              </p>
            </div>
          )}

          {phase === 'error' && (
            <div className="space-y-3 text-center">
              <p className="text-sm text-red-600">{errMsg}</p>
              <button className="btn-ghost text-sm" onClick={() => setPhase('input')}>Try again</button>
            </div>
          )}

        </div>

        <p className="text-center text-xs text-gray-400">
          Access is restricted to authorized personnel only.
        </p>
      </div>
    </div>
  )
}

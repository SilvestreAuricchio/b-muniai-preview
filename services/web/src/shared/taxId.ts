// Tax ID utilities — alphanumeric CNPJ support (Brazil, IN RFB 2.229/2024)
//
// New CNPJ format (effective July 2026): positions 1–12 may be [A-Z0-9],
// only positions 13–14 (check digits) remain numeric.
// Character values: ASCII code − 48  (0→0…9→9, A→17…Z→42).

function charValue(c: string): number {
  return c.toUpperCase().charCodeAt(0) - 48            // ASCII − 48 for all chars
}

// ---------------------------------------------------------------------------
// CNPJ

export function stripCNPJ(v: string): string {
  return v.toUpperCase().replace(/[.\-/]/g, '').replace(/[^A-Z0-9]/g, '')
}

export function maskCNPJ(raw: string): string {
  // Strip separators, uppercase, then build clean string:
  // positions 0–11 accept A-Z0-9, positions 12–13 (check digits) accept digits only.
  const src = raw.toUpperCase().replace(/[.\-/]/g, '')
  let clean = ''
  for (const ch of src) {
    if (clean.length >= 14) break
    if (clean.length < 12) {
      if (/[A-Z0-9]/.test(ch)) clean += ch
    } else {
      if (/[0-9]/.test(ch)) clean += ch
    }
  }
  const n = clean.length
  if (n <= 2)  return clean
  if (n <= 5)  return `${clean.slice(0, 2)}.${clean.slice(2)}`
  if (n <= 8)  return `${clean.slice(0, 2)}.${clean.slice(2, 5)}.${clean.slice(5)}`
  if (n <= 12) return `${clean.slice(0, 2)}.${clean.slice(2, 5)}.${clean.slice(5, 8)}/${clean.slice(8)}`
  return `${clean.slice(0, 2)}.${clean.slice(2, 5)}.${clean.slice(5, 8)}/${clean.slice(8, 12)}-${clean.slice(12)}`
}

export function validateCNPJ(raw: string): boolean {
  const clean = stripCNPJ(raw)
  if (clean.length !== 14) return false
  if (new Set(clean).size === 1) return false          // all same char
  if (!/^\d{2}$/.test(clean.slice(12))) return false  // only check digits must be numeric

  const w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
  const s1  = w1.reduce((acc, w, i) => acc + charValue(clean[i]) * w, 0)
  const r1  = s1 % 11
  const d1  = r1 < 2 ? 0 : 11 - r1
  if (parseInt(clean[12], 10) !== d1) return false

  const w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
  const s2  = w2.reduce((acc, w, i) => acc + charValue(clean[i]) * w, 0)
  const r2  = s2 % 11
  const d2  = r2 < 2 ? 0 : 11 - r2
  return parseInt(clean[13], 10) === d2
}

export function cnpjError(raw: string): string | null {
  const clean = stripCNPJ(raw)
  if (clean.length === 0) return null
  if (clean.length < 14)  return 'CNPJ must have 14 characters'
  if (!validateCNPJ(raw))  return 'Invalid CNPJ — check digit mismatch'
  return null
}

// ---------------------------------------------------------------------------
// Country dispatch

export function maskTaxId(country: string, raw: string): string {
  if (country === 'BR') return maskCNPJ(raw)
  return raw
}

export function validateTaxId(country: string, raw: string): boolean {
  if (country === 'BR') return validateCNPJ(raw)
  return true  // unknown country: skip client-side validation
}

export function taxIdError(country: string, raw: string): string | null {
  if (country === 'BR') return cnpjError(raw)
  return null
}

export function taxIdPlaceholder(country: string): string {
  if (country === 'BR') return 'XX.XXX.XXX/XXXX-XX'
  return 'Tax ID'
}

export function taxIdLabel(country: string): string {
  if (country === 'BR') return 'CNPJ'
  return 'Tax ID'
}

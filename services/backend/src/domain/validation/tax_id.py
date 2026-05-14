import re


def _char_value(c: str) -> int:
    """Numeric value of a CNPJ character: ASCII code − 48 (0→0…9→9, A→17…Z→42)."""
    return ord(c.upper()) - 48


def _validate_cnpj(raw: str) -> None:
    """
    Validate a Brazilian CNPJ (alphanumeric format, IN RFB 2.229/2024).

    Format: 14 characters total.
      - Positions 1–8  : [A-Z0-9]  (raiz)
      - Positions 9–12 : [A-Z0-9]  (filial / order)
      - Positions 13–14: [0-9]     (check digits, modulo-11)

    Character values: ASCII code − 48 (0→0…9→9, A→17…Z→42).
    """
    clean = re.sub(r'[.\-/]', '', raw.upper())

    if len(clean) != 14:
        raise ValueError(f"CNPJ must have 14 characters (got {len(clean)})")

    if not re.match(r'^[A-Z0-9]{12}\d{2}$', clean):
        raise ValueError("CNPJ: positions 13–14 must be digits")

    if len(set(clean)) == 1:
        raise ValueError("CNPJ must not consist of a single repeated character")

    # First check digit — weights over positions 1–12
    w1  = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s1  = sum(_char_value(clean[i]) * w1[i] for i in range(12))
    r1  = s1 % 11
    d1  = 0 if r1 < 2 else 11 - r1
    if int(clean[12]) != d1:
        raise ValueError("Invalid CNPJ: first check digit mismatch")

    # Second check digit — weights over positions 1–13
    w2  = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s2  = sum(_char_value(clean[i]) * w2[i] for i in range(13))
    r2  = s2 % 11
    d2  = 0 if r2 < 2 else 11 - r2
    if int(clean[13]) != d2:
        raise ValueError("Invalid CNPJ: second check digit mismatch")


# ---------------------------------------------------------------------------
# Country dispatch

_VALIDATORS: dict[str, callable] = {
    "BR": _validate_cnpj,
}


def validate_tax_id(country: str, raw: str) -> None:
    """Validate a tax ID for the given ISO-3166-1 alpha-2 country code.
    Raises ValueError with a human-readable message on failure.
    Unknown countries are silently accepted (future extensibility).
    """
    validator = _VALIDATORS.get(country.upper())
    if validator:
        validator(raw)

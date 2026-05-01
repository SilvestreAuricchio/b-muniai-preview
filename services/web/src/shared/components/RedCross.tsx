interface Props {
  size?: number
  className?: string
}

export function RedCross({ size = 24, className = '' }: Props) {
  const arm = Math.round(size * 0.27)
  const mid = Math.round(size * 0.33)

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Vertical bar */}
      <rect x={arm} y="0" width={mid} height="30" rx="2" fill="currentColor" />
      {/* Horizontal bar */}
      <rect x="0" y={arm} width="30" height={mid} rx="2" fill="currentColor" />
    </svg>
  )
}

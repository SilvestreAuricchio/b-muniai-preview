interface Props {
  label: string
  value: string | number
  detail?: string
  accent?: boolean
  icon?: string
}

export function InsightCard({ label, value, detail, accent = false, icon }: Props) {
  return (
    <div className="card flex flex-col gap-3 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-gray-500">{label}</p>
        {icon && (
          <span className={`text-xl leading-none ${accent ? 'text-brand-600' : 'text-gray-300'}`}>
            {icon}
          </span>
        )}
      </div>
      <p className={`text-3xl font-bold tabular-nums ${accent ? 'text-brand-600' : 'text-gray-900'}`}>
        {value}
      </p>
      {detail && <p className="text-xs text-gray-400">{detail}</p>}
      {accent && (
        <div className="h-0.5 w-8 rounded-full bg-brand-600 opacity-60" />
      )}
    </div>
  )
}

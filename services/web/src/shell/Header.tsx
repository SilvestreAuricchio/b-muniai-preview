import { RedCross } from '@/shared/components/RedCross'

interface Props {
  title: string
  subtitle?: string
}

export function Header({ title, subtitle }: Props) {
  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      <div>
        <h1 className="text-base font-semibold text-gray-900">{title}</h1>
        {subtitle && <p className="text-xs text-gray-400">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2 text-brand-600 opacity-20">
        <RedCross size={20} />
      </div>
    </header>
  )
}

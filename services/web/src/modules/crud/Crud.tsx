import { Header } from '@/shell/Header'
import { useParams } from 'react-router-dom'

export function Crud() {
  const { entity } = useParams<{ entity?: string }>()
  const title = entity
    ? entity.charAt(0).toUpperCase() + entity.slice(1)
    : 'Management'

  return (
    <div>
      <Header title={title} subtitle="Create, read, update, delete" />
      <div className="p-6">
        <div className="card p-8 text-center text-gray-400">
          <p className="text-sm">{title} CRUD — scaffold in progress</p>
        </div>
      </div>
    </div>
  )
}

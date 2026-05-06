import { Header } from '@/shell/Header'

export function Logs() {
  return (
    <div>
      <Header title="Audit Log" subtitle="OPERATION_LOG — append-only, stored in MongoDB" />
      <div className="p-6">
        <div className="card p-8 text-center text-gray-400">
          <p className="text-sm font-mono">Audit log viewer — coming soon</p>
        </div>
      </div>
    </div>
  )
}

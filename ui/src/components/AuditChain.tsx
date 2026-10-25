import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { auditApi } from '@/api/audit'
import { ShieldCheck, ShieldAlert, Link2 } from 'lucide-react'

export default function AuditChain() {
  const { docId } = useParams<{ docId: string }>()
  const { data, isLoading, error } = useQuery({
    queryKey: ['audit', docId],
    queryFn: () => auditApi.verifyChain(docId!),
    enabled: !!docId,
  })

  if (isLoading) return <div className="p-8 text-center text-muted-foreground">Verifying chain…</div>
  if (error || !data) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        No audit data — GET /api/review/audit needs MAILROOM_PIPELINE_URL.
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Audit Trail</h1>
        <p className="text-sm text-muted-foreground mt-1">Document: {docId}</p>
      </div>

      <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium ${
        data.chain_valid
          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
          : 'bg-red-50 text-red-700 border border-red-200'
      }`}
      >
        {data.chain_valid ? <ShieldCheck className="h-4 w-4" /> : <ShieldAlert className="h-4 w-4" />}
        {data.chain_valid ? 'Chain present' : data.error || 'Chain unavailable'}
      </div>

      <div className="space-y-0">
        {data.entries.map((entry, i) => (
          <div key={String(entry.id ?? i)} className="relative pl-8 pb-6 last:pb-0">
            {i < data.entries.length - 1 && (
              <div className="absolute left-3 top-6 bottom-0 w-px bg-border" />
            )}
            <div className="absolute left-0 top-1 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
              <Link2 className="h-3 w-3 text-primary" />
            </div>
            <div className="border border-border rounded-lg p-4 bg-card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">{String(entry.action || 'event')}</span>
                <span className="text-xs text-muted-foreground">
                  {entry.timestamp ? new Date(String(entry.timestamp)).toLocaleString() : ''}
                </span>
              </div>
              <p className="text-xs text-muted-foreground font-mono break-all">
                <span className="text-foreground">Hash:</span> {String(entry.hash || '—')}
              </p>
              <p className="text-xs text-muted-foreground font-mono break-all">
                <span className="text-foreground">Previous:</span> {String(entry.prev_hash || 'genesis')}
              </p>
            </div>
          </div>
        ))}
        {data.entries.length === 0 && (
          <p className="text-sm text-muted-foreground">Producer returned no hash-chain rows.</p>
        )}
      </div>
    </div>
  )
}

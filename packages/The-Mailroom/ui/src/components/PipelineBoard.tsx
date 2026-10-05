import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { usePipelineStore } from '@/stores/pipelineStore'
import { documentsApi } from '@/api/documents'
import DocumentCard from './DocumentCard'
import UploadDropzone from './UploadDropzone'
import ConveyorAnimation from './ConveyorAnimation'

const BINS = [
  { key: 'inbox' as const, label: 'Inbox', color: 'border-l-blue-500' },
  { key: 'processing' as const, label: 'Processing', color: 'border-l-amber-500' },
  { key: 'classified' as const, label: 'Classified', color: 'border-l-emerald-500' },
  { key: 'review' as const, label: 'Review', color: 'border-l-orange-500' },
  { key: 'failed' as const, label: 'Failed', color: 'border-l-red-500' },
  { key: 'archive' as const, label: 'Archive', color: 'border-l-slate-500' },
]

export default function PipelineBoard() {
  const { queue, setQueue } = usePipelineStore()
  const { data, isLoading } = useQuery({
    queryKey: ['queue'],
    queryFn: documentsApi.getQueue,
    refetchInterval: 5000,
  })

  useEffect(() => {
    if (data) setQueue(data)
  }, [data, setQueue])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Document Pipeline</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Langfuse traces mapped onto operator bins — not a canned floor.
          </p>
        </div>
        <UploadDropzone />
      </div>

      <ConveyorAnimation queue={queue} />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {BINS.map((bin) => (
          <div
            key={bin.key}
            className={`rounded-lg border bg-card shadow-sm ${bin.color} border-l-4`}
          >
            <div className="p-3 border-b border-border flex items-center justify-between">
              <span className="text-sm font-medium">{bin.label}</span>
              <span className="text-xs bg-muted px-2 py-0.5 rounded-full">
                {queue[bin.key]?.length || 0}
              </span>
            </div>
            <div className="p-2 space-y-2 min-h-[300px] max-h-[600px] overflow-y-auto">
              {isLoading && queue[bin.key]?.length === 0 ? (
                <div className="text-center py-8 text-sm text-muted-foreground">Loading…</div>
              ) : (
                queue[bin.key]?.map((doc) => (
                  <DocumentCard key={doc.trace_id || doc.doc_id} document={doc} />
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

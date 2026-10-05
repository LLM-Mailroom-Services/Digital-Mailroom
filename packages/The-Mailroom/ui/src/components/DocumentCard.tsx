import { usePipelineStore } from '@/stores/pipelineStore'
import type { Document } from '@/types/api'
import { FileText, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface Props {
  document: Document
}

const statusIcons = {
  inbox: Clock,
  processing: Clock,
  classified: CheckCircle,
  review: AlertTriangle,
  failed: AlertTriangle,
  archive: CheckCircle,
}

export default function DocumentCard({ document }: Props) {
  const { selectDocument, selectedDoc } = usePipelineStore()
  const Icon = statusIcons[document.status] || FileText
  const isSelected = selectedDoc?.doc_id === document.doc_id
  const stamp = document.updated_at || document.created_at

  return (
    <div
      onClick={() => selectDocument(isSelected ? null : document)}
      className={`p-3 rounded-md border cursor-pointer transition-all ${
        isSelected
          ? 'border-primary bg-primary/5'
          : 'border-border bg-background hover:border-muted-foreground/30'
      }`}
    >
      <div className="flex items-start gap-2">
        <Icon className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium truncate">{document.filename || document.doc_id}</p>
          <p className="text-xs text-muted-foreground truncate">{document.doc_type}</p>
          <div className="mt-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Confidence</span>
              <span className={document.confidence > 0.9 ? 'text-emerald-600' : document.confidence > 0.7 ? 'text-amber-600' : 'text-red-600'}>
                {Math.round(document.confidence * 100)}%
              </span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  document.confidence > 0.9
                    ? 'bg-emerald-500'
                    : document.confidence > 0.7
                      ? 'bg-amber-500'
                      : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(100, document.confidence * 100)}%` }}
              />
            </div>
          </div>
          {stamp && (
            <p className="text-[10px] text-muted-foreground mt-1.5">
              {formatDistanceToNow(new Date(stamp), { addSuffix: true })}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

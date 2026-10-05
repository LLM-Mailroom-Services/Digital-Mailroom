import { useState } from 'react'
import { Upload, X } from 'lucide-react'

/** Ingest lives on llm-mailroom (:8000). This visualizer does not accept uploads. */
export default function UploadDropzone() {
  const [open, setOpen] = useState(false)

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:opacity-90"
      >
        <Upload className="h-4 w-4" />
        Ingest hint
      </button>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="w-full max-w-md p-6 rounded-xl bg-card border border-border shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Document ingest</h2>
          <button type="button" onClick={() => setOpen(false)} className="p-1 rounded-md hover:bg-muted">
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="text-sm text-muted-foreground">
          This desk reads Langfuse traces and operator archive/ops. Drop files on
          the llm-mailroom producer inbox (`MAILROOM_PIPELINE_URL`, default
          :8000) — The-Mailroom never fabricates envelopes or accepts uploads.
        </p>
        <div className="mt-4 flex justify-end">
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

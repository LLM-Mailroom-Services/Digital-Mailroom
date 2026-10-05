import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { reviewApi } from '@/api/review'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle, XCircle, FileText, ChevronRight } from 'lucide-react'
import type { Document, ReviewResolution } from '@/types/api'

export default function ReviewPanel() {
  const { data: docs, isLoading, error } = useQuery({
    queryKey: ['review-queue'],
    queryFn: reviewApi.getReviewQueue,
    refetchInterval: 3000,
  })
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
  const [comment, setComment] = useState('')
  const [disposition, setDisposition] = useState<ReviewResolution['disposition']>('resume')
  const queryClient = useQueryClient()

  const resolveMutation = useMutation({
    mutationFn: ({ doc, resolution }: { doc: Document; resolution: 'approved' | 'rejected' }) =>
      reviewApi.resolve(doc, { resolution, comment, disposition }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['review-queue'] })
      void queryClient.invalidateQueries({ queryKey: ['queue'] })
      setSelectedDoc(null)
      setComment('')
    },
  })

  const { data: preview } = useQuery({
    queryKey: ['preview', selectedDoc?.doc_id, selectedDoc?.trace_id],
    queryFn: () => reviewApi.source(selectedDoc!),
    enabled: !!selectedDoc,
  })

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Loading review queue…</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Human Review Queue</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {docs?.length || 0} documents awaiting review (Langfuse + producer proxy)
        </p>
        {error ? (
          <p className="text-sm text-destructive mt-2">
            Review queue unavailable. Display stays Langfuse-only; resolve needs MAILROOM_PIPELINE_URL.
          </p>
        ) : null}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-2">
          {docs?.map((doc) => (
            <button
              type="button"
              key={doc.trace_id || doc.doc_id}
              onClick={() => setSelectedDoc(doc)}
              className={`w-full text-left p-4 rounded-lg border transition-all ${
                selectedDoc?.doc_id === doc.doc_id
                  ? 'border-primary bg-primary/5'
                  : 'border-border bg-card hover:border-muted-foreground/30'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">{doc.filename || doc.doc_id}</p>
                    <p className="text-xs text-muted-foreground">
                      {doc.doc_type} — {doc.review_reason || doc.verdict || 'needs review'}
                    </p>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </button>
          ))}
          {(!docs || docs.length === 0) && (
            <div className="text-center py-12 text-muted-foreground border border-dashed border-border rounded-lg">
              No documents in review queue
            </div>
          )}
        </div>

        {selectedDoc && (
          <div className="border border-border rounded-lg bg-card p-6 space-y-4">
            <div>
              <h3 className="font-medium">{selectedDoc.filename || selectedDoc.doc_id}</h3>
              <p className="text-sm text-muted-foreground">{selectedDoc.doc_type}</p>
              <Link
                to={`/audit/${selectedDoc.doc_id}`}
                className="text-xs text-muted-foreground underline"
              >
                Audit trail
              </Link>
            </div>

            <div className="border border-border rounded-md p-4 bg-background min-h-[160px] max-h-[320px] overflow-auto">
              {preview?.text ? (
                <pre className="text-xs whitespace-pre-wrap">{preview.text}</pre>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {preview?.error || 'No parked text (producer source / lookup fallback).'}
                </p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium">Disposition</label>
              <select
                value={disposition}
                onChange={(e) => setDisposition(e.target.value as ReviewResolution['disposition'])}
                className="w-full mt-1 px-3 py-2 rounded-md border border-input bg-background text-sm"
              >
                <option value="resume">resume</option>
                <option value="record">record</option>
                <option value="requeue">requeue</option>
                <option value="complete">complete</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium">Review comment</label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="w-full mt-1 px-3 py-2 rounded-md border border-input bg-background text-sm"
                rows={3}
                placeholder="Optional notes forwarded to the producer"
              />
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => resolveMutation.mutate({ doc: selectedDoc, resolution: 'approved' })}
                disabled={resolveMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 py-2 rounded-md bg-emerald-600 text-white text-sm font-medium disabled:opacity-50"
              >
                <CheckCircle className="h-4 w-4" />
                Approve
              </button>
              <button
                type="button"
                onClick={() => resolveMutation.mutate({ doc: selectedDoc, resolution: 'rejected' })}
                disabled={resolveMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 py-2 rounded-md bg-red-600 text-white text-sm font-medium disabled:opacity-50"
              >
                <XCircle className="h-4 w-4" />
                Reject
              </button>
            </div>
            {resolveMutation.isError && (
              <p className="text-sm text-destructive">
                Resolve failed — producer must be configured on the visualizer.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

import { api } from './client'
import type { BinStatus, Document, Matter, PipelineQueue } from '@/types/api'

const emptyQueue = (): PipelineQueue => ({
  inbox: [],
  processing: [],
  classified: [],
  review: [],
  failed: [],
  archive: [],
})

export function stageToBin(stage: string | undefined): BinStatus {
  const value = String(stage || '').toLowerCase()
  if (value === 'inbox') return 'inbox'
  if (value === 'review') return 'review'
  if (value === 'failed') return 'failed'
  if (value === 'archive' || value === 'archived' || value === 'catalog') return 'archive'
  if (value === 'classify' || value === 'classified' || value === 'retry_classify') return 'classified'
  return 'processing'
}

export function runToDocument(run: Record<string, unknown>): Document {
  const stage = String(run.stage || 'unknown')
  const created = String(run.created_at || run.updated_at || '')
  return {
    doc_id: String(run.doc_id || run.trace_id || ''),
    trace_id: String(run.trace_id || ''),
    filename: String(run.filename || run.doc_id || run.trace_id || ''),
    matter_id: String(run.matter_id || run.session_id || ''),
    doc_type: String(run.doc_type || 'unknown'),
    doc_subclass: run.doc_subclass ? String(run.doc_subclass) : undefined,
    confidence: Number(
      run.extraction_confidence ?? run.classification_confidence ?? 0,
    ),
    status: stageToBin(stage),
    stage,
    created_at: created,
    updated_at: String(run.updated_at || created),
    review_reason: run.escalation_reason
      ? String(run.escalation_reason)
      : Array.isArray(run.review_causes)
        ? (run.review_causes as string[]).join(', ')
        : undefined,
    verdict: run.verdict ? String(run.verdict) : undefined,
    needs_human: Boolean(run.needs_human),
  }
}

export const documentsApi = {
  getQueue: async (): Promise<PipelineQueue> => {
    const res = await api.get('/api/traces', { params: { since: 604800, limit: 200 } })
    const queue = emptyQueue()
    for (const run of res.data.runs || []) {
      const doc = runToDocument(run)
      queue[doc.status].push(doc)
    }
    return queue
  },

  listMatters: async (): Promise<Matter[]> => {
    const res = await api.get('/api/sessions', { params: { limit: 50 } })
    return (res.data.sessions || []).map((session: Record<string, unknown>) => ({
      matter_id: String(session.id || ''),
      client: String(session.id || ''),
      created_at: session.created_at ? String(session.created_at) : undefined,
    }))
  },
}

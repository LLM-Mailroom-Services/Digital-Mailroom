import { api } from './client'
import { runToDocument } from './documents'
import type { Document, ReviewResolution } from '@/types/api'

export const reviewApi = {
  getReviewQueue: async (): Promise<Document[]> => {
    const res = await api.get('/api/review-queue', { params: { since: 604800 } })
    return (res.data.runs || []).map((run: Record<string, unknown>) => runToDocument(run))
  },

  source: async (doc: Document) => {
    const res = await api.get('/api/review/source', {
      params: { doc_id: doc.doc_id, trace_id: doc.trace_id, filename: doc.filename },
    })
    return res.data as { text?: string; error?: string; configured?: boolean }
  },

  resolve: (doc: Document, resolution: ReviewResolution) =>
    api.post('/api/review/resolve', {
      decision: resolution.resolution,
      disposition: resolution.disposition || 'resume',
      notes: resolution.comment || '',
      doc_id: doc.doc_id,
      trace_id: doc.trace_id,
      filename: doc.filename,
      doc_type: resolution.doc_type || doc.doc_type,
      extracted_data: resolution.extracted_data,
    }).then((r) => r.data),
}

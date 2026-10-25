import { api } from './client'
import type { AuditEntry } from '@/types/api'

function asEntries(payload: unknown): AuditEntry[] {
  if (Array.isArray(payload)) return payload as AuditEntry[]
  if (payload && typeof payload === 'object') {
    const data = payload as Record<string, unknown>
    for (const key of ['entries', 'audit', 'chain', 'events', 'rows']) {
      if (Array.isArray(data[key])) return data[key] as AuditEntry[]
    }
  }
  return []
}

export const auditApi = {
  getAuditTrail: async (docId: string): Promise<AuditEntry[]> => {
    const res = await api.get('/api/review/audit', { params: { doc_id: docId } })
    return asEntries(res.data)
  },

  verifyChain: async (docId: string) => {
    const res = await api.get('/api/review/audit', { params: { doc_id: docId } })
    const entries = asEntries(res.data)
    const valid = res.data?.valid ?? res.data?.chain_valid ?? res.data?.ok
    return {
      chain_valid: valid !== false && !res.data?.error,
      entries,
      error: res.data?.error ? String(res.data.error) : undefined,
    }
  },
}

import { api } from './client'
import type { ArchiveEntry } from '@/types/api'

export const archiveApi = {
  list: (params?: { matter_id?: string; doc_type?: string }) =>
    api.get<ArchiveEntry[]>('/v1/archive/list', { params }).then((r) => r.data),

  download: (docId: string) =>
    api.get(`/v1/archive/${docId}/download`, { responseType: 'blob' }).then((r) => r.data as Blob),

  preview: (docId: string) =>
    api.get<{ content: string | null; type: string; mime: string }>(
      `/v1/archive/${docId}/preview`,
    ).then((r) => r.data),

  verify: (docId: string) =>
    api.get<{ valid: boolean; computed?: string; expected?: string | null; reason?: string | null }>(
      `/v1/archive/${docId}/verify`,
    ).then((r) => r.data),
}

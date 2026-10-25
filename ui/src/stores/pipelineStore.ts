import { create } from 'zustand'
import type { Document, PipelineQueue } from '@/types/api'

interface PipelineState {
  queue: PipelineQueue
  selectedDoc: Document | null
  setQueue: (queue: PipelineQueue) => void
  updateDocumentStage: (docId: string, stage: string) => void
  addDocument: (doc: Document) => void
  selectDocument: (doc: Document | null) => void
}

const emptyQueue: PipelineQueue = {
  inbox: [],
  processing: [],
  classified: [],
  review: [],
  failed: [],
  archive: [],
}

function allDocs(queue: PipelineQueue): Document[] {
  return [
    ...queue.inbox,
    ...queue.processing,
    ...queue.classified,
    ...queue.review,
    ...queue.failed,
    ...queue.archive,
  ]
}

export const usePipelineStore = create<PipelineState>((set, get) => ({
  queue: emptyQueue,
  selectedDoc: null,

  setQueue: (queue) => set({ queue }),

  updateDocumentStage: (docId, stage) => {
    const { queue } = get()
    const next: PipelineQueue = { ...emptyQueue, inbox: [], processing: [], classified: [], review: [], failed: [], archive: [] }
    const found = allDocs(queue).find((d) => d.doc_id === docId)
    const rest = allDocs(queue).filter((d) => d.doc_id !== docId)
    if (found) {
      found.status = (['inbox', 'processing', 'classified', 'review', 'failed', 'archive'].includes(stage)
        ? stage
        : 'processing') as Document['status']
      found.stage = stage
      rest.push(found)
    }
    rest.forEach((doc) => {
      next[doc.status].push(doc)
    })
    set({ queue: next })
  },

  addDocument: (doc) => {
    const { queue } = get()
    set({
      queue: {
        ...queue,
        [doc.status]: [doc, ...queue[doc.status]],
      },
    })
  },

  selectDocument: (doc) => set({ selectedDoc: doc }),
}))

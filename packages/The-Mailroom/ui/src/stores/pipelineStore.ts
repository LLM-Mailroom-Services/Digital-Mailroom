import { create } from 'zustand'
import { stageToBin } from '@/api/documents'
import type { Document, PipelineQueue } from '@/types/api'

interface PipelineState {
  queue: PipelineQueue
  selectedDoc: Document | null
  /** Doc ids recently touched by WebSocket — poll must not clobber until confirmed. */
  wsPinned: Set<string>
  setQueue: (queue: PipelineQueue) => void
  mergePolledQueue: (polled: PipelineQueue) => void
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

function rebuildQueue(docs: Document[]): PipelineQueue {
  const next: PipelineQueue = { ...emptyQueue, inbox: [], processing: [], classified: [], review: [], failed: [], archive: [] }
  docs.forEach((doc) => {
    next[doc.status].push(doc)
  })
  return next
}

export function mergeQueueWithPoll(polled: PipelineQueue, local: PipelineQueue, pinned: Set<string>): PipelineQueue {
  const polledById = new Map(allDocs(polled).map((d) => [d.doc_id, d]))
  const merged = new Map<string, Document>()
  for (const doc of allDocs(polled)) {
    merged.set(doc.doc_id, doc)
  }
  for (const doc of allDocs(local)) {
    if (!doc.doc_id) continue
    if (pinned.has(doc.doc_id)) {
      const remote = polledById.get(doc.doc_id)
      if (!remote || remote.stage !== doc.stage || remote.status !== doc.status) {
        merged.set(doc.doc_id, doc)
        continue
      }
    } else if (!merged.has(doc.doc_id)) {
      merged.set(doc.doc_id, doc)
    }
  }
  return rebuildQueue([...merged.values()])
}

export const usePipelineStore = create<PipelineState>((set, get) => ({
  queue: emptyQueue,
  selectedDoc: null,
  wsPinned: new Set(),

  setQueue: (queue) => set({ queue, wsPinned: new Set() }),

  mergePolledQueue: (polled) => {
    const { queue, wsPinned } = get()
    const nextPinned = new Set(wsPinned)
    for (const doc of allDocs(polled)) {
      const pin = wsPinned.has(doc.doc_id)
      if (pin) {
        const local = allDocs(queue).find((d) => d.doc_id === doc.doc_id)
        if (local && local.stage === doc.stage && local.status === doc.status) {
          nextPinned.delete(doc.doc_id)
        }
      }
    }
    set({
      queue: mergeQueueWithPoll(polled, queue, wsPinned),
      wsPinned: nextPinned,
    })
  },

  updateDocumentStage: (docId, stage) => {
    const { queue } = get()
    const next: PipelineQueue = { ...emptyQueue, inbox: [], processing: [], classified: [], review: [], failed: [], archive: [] }
    const found = allDocs(queue).find((d) => d.doc_id === docId)
    const rest = allDocs(queue).filter((d) => d.doc_id !== docId)
    if (found) {
      found.status = stageToBin(stage)
      found.stage = stage
      rest.push(found)
    }
    rest.forEach((doc) => {
      next[doc.status].push(doc)
    })
    const pinned = new Set(get().wsPinned)
    pinned.add(docId)
    set({ queue: next, wsPinned: pinned })
  },

  addDocument: (doc) => {
    const { queue, wsPinned } = get()
    const pinned = new Set(wsPinned)
    if (doc.doc_id) pinned.add(doc.doc_id)
    set({
      queue: {
        ...queue,
        [doc.status]: [doc, ...queue[doc.status]],
      },
      wsPinned: pinned,
    })
  },

  selectDocument: (doc) => set({ selectedDoc: doc }),
}))

export type BinStatus =
  | 'inbox'
  | 'processing'
  | 'classified'
  | 'review'
  | 'failed'
  | 'archive'

export interface Document {
  doc_id: string
  trace_id: string
  filename: string
  matter_id: string
  doc_type: string
  doc_subclass?: string
  confidence: number
  status: BinStatus
  stage: string
  created_at: string
  updated_at: string
  review_reason?: string
  verdict?: string
  needs_human?: boolean
  extracted_fields?: Record<string, unknown>
}

export interface Matter {
  matter_id: string
  client: string
  created_at?: string
}

export interface AuditEntry {
  id?: number | string
  doc_id?: string
  hash?: string
  prev_hash?: string
  timestamp?: string
  action?: string
  [key: string]: unknown
}

export interface PipelineQueue {
  inbox: Document[]
  processing: Document[]
  classified: Document[]
  review: Document[]
  failed: Document[]
  archive: Document[]
}

export interface ReviewResolution {
  resolution: 'approved' | 'rejected'
  disposition?: 'resume' | 'record' | 'requeue' | 'complete'
  comment?: string
  doc_type?: string
  extracted_data?: Record<string, unknown>
}

export interface OpsStatus {
  throughput: number
  accuracy: number
  queue_depth: number
  active_agents: number
  avg_processing_time_ms: number
  source?: string
  total_docs?: number
}

export interface ArchiveEntry {
  doc_id: string
  matter_id: string
  doc_type: string
  archive_path: string
  file_size_bytes?: number
  checksum_sha256?: string
  archived_at: string
}

export interface UserProfile {
  username: string
  role: 'admin' | 'reviewer' | 'viewer' | string
}

export interface WSEvent {
  type: string
  [key: string]: unknown
}

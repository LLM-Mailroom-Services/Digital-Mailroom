const explicit = (import.meta.env.VITE_WS_URL || '').replace(/\/+$/, '')

function wsOrigin(): string {
  if (explicit) return explicit
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}`
}

export class PipelineWebSocket {
  private ws: WebSocket | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private listeners: Set<(event: unknown) => void> = new Set()
  private matterId: string | null = null
  private closed = false
  private backoffMs = 3000
  private readonly maxBackoffMs = 30000
  private onConnectionChange: ((connected: boolean) => void) | null = null

  connect(matterId?: string, onConnectionChange?: (connected: boolean) => void) {
    this.closed = false
    this.matterId = matterId || null
    if (onConnectionChange) this.onConnectionChange = onConnectionChange
    const url = `${wsOrigin()}/ws/pipeline`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this.backoffMs = 3000
      const token = localStorage.getItem('mailroom_token') || ''
      if (token) {
        this.ws?.send(JSON.stringify({ action: 'auth', token }))
      }
      this.onConnectionChange?.(true)
      if (this.matterId) {
        this.ws?.send(JSON.stringify({ action: 'subscribe', matter_id: this.matterId }))
      }
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.listeners.forEach((cb) => cb(data))
      } catch {
        /* ignore non-JSON */
      }
    }

    this.ws.onerror = () => {
      this.onConnectionChange?.(false)
    }

    this.ws.onclose = () => {
      this.onConnectionChange?.(false)
      if (this.closed) return
      const delay = this.backoffMs
      this.backoffMs = Math.min(this.backoffMs * 2, this.maxBackoffMs)
      this.reconnectTimer = setTimeout(() => this.connect(this.matterId || undefined), delay)
    }
  }

  onMessage(callback: (event: unknown) => void) {
    this.listeners.add(callback)
    return () => {
      this.listeners.delete(callback)
    }
  }

  disconnect() {
    this.closed = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.onConnectionChange?.(false)
    this.ws?.close()
    this.ws = null
  }
}

export const pipelineWS = new PipelineWebSocket()

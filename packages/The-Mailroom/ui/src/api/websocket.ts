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

  connect(matterId?: string) {
    this.closed = false
    this.matterId = matterId || null
    const token = localStorage.getItem('mailroom_token') || ''
    const params = new URLSearchParams()
    if (token) params.set('token', token)
    const query = params.toString()
    const url = `${wsOrigin()}/ws/pipeline${query ? `?${query}` : ''}`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
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

    this.ws.onclose = () => {
      if (this.closed) return
      this.reconnectTimer = setTimeout(() => this.connect(this.matterId || undefined), 3000)
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
    this.ws?.close()
    this.ws = null
  }
}

export const pipelineWS = new PipelineWebSocket()

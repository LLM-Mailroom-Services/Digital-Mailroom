import { useWSStore } from '@/stores/websocketStore'

export function useWebSocket() {
  return useWSStore()
}

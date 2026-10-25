import { create } from 'zustand'

interface WSState {
  connected: boolean
  lastEvent: unknown | null
  setConnected: (c: boolean) => void
  setLastEvent: (e: unknown) => void
}

export const useWSStore = create<WSState>((set) => ({
  connected: false,
  lastEvent: null,
  setConnected: (connected) => set({ connected }),
  setLastEvent: (lastEvent) => set({ lastEvent }),
}))

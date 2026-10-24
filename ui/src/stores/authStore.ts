import { create } from 'zustand'
import { api } from '@/api/client'
import type { UserProfile } from '@/types/api'

interface AuthState {
  token: string | null
  user: UserProfile | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  fetchProfile: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('mailroom_token'),
  user: null,
  isAuthenticated: !!localStorage.getItem('mailroom_token'),

  login: async (username, password) => {
    const res = await api.post('/v1/auth/login', { username, password })
    const { access_token, role } = res.data
    localStorage.setItem('mailroom_token', access_token)
    set({ token: access_token, isAuthenticated: true, user: { username, role } })
  },

  logout: async () => {
    try {
      await api.post('/v1/auth/logout')
    } catch {
      /* token already gone */
    }
    localStorage.removeItem('mailroom_token')
    set({ token: null, user: null, isAuthenticated: false })
  },

  fetchProfile: async () => {
    const res = await api.get('/v1/auth/me')
    set({ user: res.data })
  },
}))

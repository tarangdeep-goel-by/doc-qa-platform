import { create } from 'zustand'
import * as authApi from '../api/authClient'
import type { User } from '../types'

interface AuthState {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  authRequired: boolean

  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<boolean>
  loadUser: () => Promise<void>
  getToken: () => string | null
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: true,
  authRequired: true,

  login: async (email: string, password: string) => {
    const data = await authApi.login(email, password)
    set({
      user: data.user,
      accessToken: data.access_token,
      isAuthenticated: true,
    })
  },

  logout: async () => {
    try {
      await authApi.logout()
    } catch {
      // ignore
    }
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
    })
  },

  refresh: async () => {
    try {
      const data = await authApi.refresh()
      set({
        user: data.user,
        accessToken: data.access_token,
        isAuthenticated: true,
      })
      return true
    } catch {
      set({
        user: null,
        accessToken: null,
        isAuthenticated: false,
      })
      return false
    }
  },

  loadUser: async () => {
    set({ isLoading: true })

    // Check if backend requires auth
    try {
      const res = await fetch('/health')
      if (res.ok) {
        const data = await res.json()
        if (data.auth_required === false) {
          // B2C mode — skip auth, set anonymous user
          set({
            authRequired: false,
            isAuthenticated: true,
            user: { id: '', email: 'anonymous', role: 'admin' },
            isLoading: false,
          })
          return
        }
      }
    } catch {
      // Health check failed — fall through to normal auth flow
    }

    const ok = await get().refresh()
    set({ isLoading: false })
    if (!ok) {
      set({ isAuthenticated: false })
    }
  },

  getToken: () => get().accessToken,
}))

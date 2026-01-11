import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types/auth'
import { login as apiLogin, logout as apiLogout, getCurrentUser, refreshToken as apiRefreshToken } from '@/api/auth'
import { setTokens, clearTokens, getAccessToken, getRefreshToken } from '@/api/client'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  isCheckingAuth: boolean
  error: string | null

  // Actions
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
  refreshTokens: () => Promise<boolean>
  clearError: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      isCheckingAuth: true,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const tokens = await apiLogin({ email, password })
          setTokens(tokens.access_token, tokens.refresh_token)

          // Fetch user profile
          const userResponse = await getCurrentUser()
          set({
            user: userResponse.data || null,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Login failed',
            isLoading: false,
          })
          throw error
        }
      },

      logout: async () => {
        try {
          await apiLogout()
        } catch {
          // Ignore logout errors
        } finally {
          clearTokens()
          set({
            user: null,
            isAuthenticated: false,
            error: null,
          })
        }
      },

      checkAuth: async () => {
        const accessToken = getAccessToken()
        if (!accessToken) {
          set({ isCheckingAuth: false, isAuthenticated: false, user: null })
          return
        }

        set({ isCheckingAuth: true })
        try {
          const userResponse = await getCurrentUser()
          set({
            user: userResponse.data || null,
            isAuthenticated: true,
            isCheckingAuth: false,
          })
        } catch (error) {
          // Try to refresh token
          const refreshed = await get().refreshTokens()
          if (!refreshed) {
            clearTokens()
            set({
              user: null,
              isAuthenticated: false,
              isCheckingAuth: false,
            })
          } else {
            set({ isCheckingAuth: false })
          }
        }
      },

      refreshTokens: async () => {
        const token = getRefreshToken()
        if (!token) return false

        try {
          const tokens = await apiRefreshToken(token)
          setTokens(tokens.access_token, tokens.refresh_token)

          // Fetch updated user profile
          const userResponse = await getCurrentUser()
          set({
            user: userResponse.data || null,
            isAuthenticated: true,
          })
          return true
        } catch {
          return false
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        // Only persist the user info, not loading state or tokens (those are in localStorage separately)
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

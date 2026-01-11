export interface User {
  user_id: string
  email: string
  full_name: string | null
  role: 'admin' | 'user'
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RefreshRequest {
  refresh_token: string
}

export interface UserCreateRequest {
  email: string
  password: string
  full_name?: string
  role?: 'admin' | 'user'
}

export interface UserUpdateRequest {
  email?: string
  password?: string
  full_name?: string
  role?: 'admin' | 'user'
  is_active?: boolean
}

export interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

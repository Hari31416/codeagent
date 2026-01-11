import type { ApiResponse } from '@/types/api'
import type { LoginRequest, TokenResponse, User, UserCreateRequest, UserUpdateRequest } from '@/types/auth'
import { getAuthHeaders, handleAuthError } from './client'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8011/api/v1'

export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }))
    throw new Error(error.detail || 'Login failed')
  }

  return response.json()
}

export async function refreshToken(token: string): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh_token: token }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Token refresh failed' }))
    throw new Error(error.detail || 'Token refresh failed')
  }

  return response.json()
}

export async function getCurrentUser(): Promise<ApiResponse<User>> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    handleAuthError(response.status)
    const error = await response.json().catch(() => ({ detail: 'Failed to get user' }))
    throw new Error(error.detail || 'Failed to get user')
  }

  return response.json()
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: getAuthHeaders(),
    })
  } catch {
    // Ignore logout errors - we'll clear tokens anyway
  }
}

// User management (admin only)

export async function listUsers(limit = 100, offset = 0): Promise<ApiResponse<User[]>> {
  const response = await fetch(`${API_BASE_URL}/users?limit=${limit}&offset=${offset}`, {
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    handleAuthError(response.status)
    const error = await response.json().catch(() => ({ detail: 'Failed to list users' }))
    throw new Error(error.detail || 'Failed to list users')
  }

  return response.json()
}

export async function createUser(userData: UserCreateRequest): Promise<ApiResponse<User>> {
  const response = await fetch(`${API_BASE_URL}/users`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(userData),
  })

  if (!response.ok) {
    handleAuthError(response.status)
    const error = await response.json().catch(() => ({ detail: 'Failed to create user' }))
    throw new Error(error.detail || 'Failed to create user')
  }

  return response.json()
}

export async function updateUser(userId: string, userData: UserUpdateRequest): Promise<ApiResponse<User>> {
  const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
    method: 'PATCH',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(userData),
  })

  if (!response.ok) {
    handleAuthError(response.status)
    const error = await response.json().catch(() => ({ detail: 'Failed to update user' }))
    throw new Error(error.detail || 'Failed to update user')
  }

  return response.json()
}

export async function deleteUser(userId: string): Promise<ApiResponse<{ message: string }>> {
  const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    handleAuthError(response.status)
    const error = await response.json().catch(() => ({ detail: 'Failed to delete user' }))
    throw new Error(error.detail || 'Failed to delete user')
  }

  return response.json()
}

import type { StreamEvent } from '@/types/api'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8011/api/v1'

// Auth token storage keys
const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

// Get stored tokens
export function getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
}

// Store tokens
export function setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
}

// Clear tokens
export function clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
}

// Get auth headers for API requests
export function getAuthHeaders(): HeadersInit {
    const token = getAccessToken()
    return token
        ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        : { 'Content-Type': 'application/json' }
}

// Handle auth errors (401 = redirect to login)
export function handleAuthError(status: number): void {
    if (status === 401) {
        clearTokens()
        // Redirect to login page
        window.location.href = '/login'
    }
}

export async function apiRequest<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`

    const response = await fetch(url, {
        ...options,
        headers: {
            ...getAuthHeaders(),
            ...options.headers,
        },
    })

    if (!response.ok) {
        // Handle auth errors
        handleAuthError(response.status)
        const error = await response.json().catch(() => ({ error: 'Request failed' }))
        throw new Error(error.error || error.detail || error.message || 'Request failed')
    }

    return response.json()
}

export function createSSEConnection(
    endpoint: string,
    onEvent: (event: StreamEvent) => void,
    onError: (error: Error) => void
): EventSource {
    const url = `${API_BASE_URL}${endpoint}`
    const eventSource = new EventSource(url)

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data) as StreamEvent
            onEvent(data)
        } catch (e) {
            console.error('Failed to parse SSE event:', e)
        }
    }

    eventSource.onerror = (event) => {
        console.error('SSE error:', event)
        onError(new Error('Connection lost'))
        eventSource.close()
    }

    return eventSource
}


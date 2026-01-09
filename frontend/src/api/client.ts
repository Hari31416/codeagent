import type { StreamEvent } from '@/types/api'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8011/api/v1'

export async function apiRequest<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`

    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    })

    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Request failed' }))
        throw new Error(error.error || error.message || 'Request failed')
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

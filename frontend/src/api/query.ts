import type { QueryRequest, StreamEvent } from '@/types/api'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8011/api/v1'

export async function* streamQuery(
  sessionId: string,
  request: QueryRequest
): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await fetch(
    `${API_BASE_URL}/sessions/${sessionId}/query`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(request),
    }
  )

  if (!response.ok) {
    throw new Error(`Query failed: ${response.statusText}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('No response body')
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    
    // Keep the last potentially incomplete line in the buffer
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const jsonStr = line.slice(6).trim()
        if (jsonStr) {
          try {
            yield JSON.parse(jsonStr) as StreamEvent
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    }
  }
}

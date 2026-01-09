import { useState, useCallback, useRef } from 'react'
import { streamQuery } from '@/api/query'
import * as sessionApi from '@/api/sessions'
import type { Message } from '@/types/message'
import type { StreamEventType } from '@/types/api'

interface UseChatOptions {
  sessionId: string
  onArtifactsCreated?: (artifactIds: string[]) => void
}

interface ChatState {
  status: StreamEventType | 'idle'
  currentThought: string | null
  currentCode: string | null
  iteration: number
  totalIterations: number
}

export function useChat({ sessionId, onArtifactsCreated }: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([])
  const [state, setState] = useState<ChatState>({
    status: 'idle',
    currentThought: null,
    currentCode: null,
    iteration: 0,
    totalIterations: 0,
  })
  const [error, setError] = useState<Error | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(async (
    content: string,
    fileIds?: string[]
  ) => {
    if (!sessionId) return

    // Add user message immediately
    const userMessage: Message = {
      message_id: crypto.randomUUID(),
      session_id: sessionId,
      role: 'user',
      content,
      artifact_ids: fileIds || [],
      is_error: false,
      created_at: new Date().toISOString(),
      metadata: {},
    }

    setMessages(prev => [...prev, userMessage])
    setError(null)
    setState(prev => ({ ...prev, status: 'started' }))

    try {
      let assistantContent = ''
      let assistantCode: string | undefined
      let assistantThoughts: string | undefined
      let artifactIds: string[] = []

      for await (const event of streamQuery(sessionId, {
        query: content,
        file_ids: fileIds,
      })) {
        // Update state based on event
        setState(prev => ({
          ...prev,
          status: event.event_type,
          iteration: event.iteration || prev.iteration,
          totalIterations: event.total_iterations || prev.totalIterations,
          currentThought: event.event_type === 'thinking'
            ? event.message
            : prev.currentThought,
          currentCode: event.event_type === 'generating_code' && event.data?.code
            ? event.data.code as string
            : prev.currentCode,
        }))

        // Handle completion
        if (event.type === 'completed' && event.data) {
          assistantContent = (event.data.result as Record<string, unknown>)?.answer as string || event.message
          assistantCode = (event.data.result as Record<string, unknown>)?.code as string | undefined
          assistantThoughts = (event.data.result as Record<string, unknown>)?.thoughts as string | undefined
          artifactIds = event.data.artifact_ids as string[] || []

          if (artifactIds.length > 0 && onArtifactsCreated) {
            onArtifactsCreated(artifactIds)
          }
        }

        // Handle errors
        if (event.type === 'error') {
          throw new Error(event.message)
        }
      }

      // Add assistant message
      const assistantMessage: Message = {
        message_id: crypto.randomUUID(),
        session_id: sessionId,
        role: 'assistant',
        content: assistantContent,
        code: assistantCode,
        thoughts: assistantThoughts,
        artifact_ids: artifactIds,
        is_error: false,
        created_at: new Date().toISOString(),
        metadata: {},
      }

      setMessages(prev => [...prev, assistantMessage])
      setState({
        status: 'idle',
        currentThought: null,
        currentCode: null,
        iteration: 0,
        totalIterations: 0,
      })

    } catch (e) {
      setError(e as Error)
      setState(prev => ({ ...prev, status: 'error' }))

      // Add error message
      setMessages(prev => [...prev, {
        message_id: crypto.randomUUID(),
        session_id: sessionId,
        role: 'assistant',
        content: (e as Error).message,
        artifact_ids: [],
        is_error: true,
        created_at: new Date().toISOString(),
        metadata: {},
      }])
    }
  }, [sessionId, onArtifactsCreated])

  const cancelQuery = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      setState(prev => ({ ...prev, status: 'cancelled' }))
    }
  }, [])

  const loadHistory = useCallback(async () => {
    if (!sessionId) return

    const response = await sessionApi.getSessionHistory(sessionId)
    if (response.success && response.data) {
      setMessages(response.data.messages)
    }
  }, [sessionId])

  return {
    messages,
    state,
    error,
    sendMessage,
    cancelQuery,
    loadHistory,
    isProcessing: state.status !== 'idle' && state.status !== 'error',
  }
}

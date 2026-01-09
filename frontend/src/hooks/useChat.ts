import { useState, useCallback, useRef, useEffect } from 'react'
import { streamQuery } from '@/api/query'
import * as sessionApi from '@/api/sessions'
import type { Message } from '@/types/message'
import type { StreamEventType } from '@/types/api'

interface UseChatOptions {
  sessionId: string
  onArtifactsCreated?: (artifactIds: string[]) => void
  onSessionRenamed?: () => void
}

interface ChatState {
  status: StreamEventType | 'idle'
  currentThought: string | null
  currentCode: string | null
  iteration: number
  totalIterations: number
}

export function useChat({ sessionId, onArtifactsCreated, onSessionRenamed }: UseChatOptions) {
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
    fileIds?: string[],
    model?: string
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

    // Auto-rename session if it's the first message
    if (messages.length === 0) {
      // Don't await this to avoid blocking the UI
      sessionApi.updateSession(sessionId, {
        name: content.slice(0, 50) + (content.length > 50 ? '...' : '')
      }).then(() => {
        onSessionRenamed?.()
      }).catch(console.error)
    }

    const assistantMessageId = crypto.randomUUID()
    const assistantMessageCreatedAt = new Date().toISOString()

    // Create initial empty assistant message
    setMessages(prev => [...prev, {
      message_id: assistantMessageId,
      session_id: sessionId,
      role: 'assistant',
      content: '', // Start empty
      artifact_ids: [],
      iterations: [],
      is_error: false,
      created_at: assistantMessageCreatedAt,
      metadata: {},
    }])

    try {
      let iterations: import('@/types/api').IterationOutput[] = []
      let assistantContent = ''
      let artifactIds: string[] = []
      let assistantArtifacts: Array<{
        artifact_id: string
        url: string
        file_name: string
        file_type: string
      }> | undefined

      for await (const event of streamQuery(sessionId, {
        query: content,
        file_ids: fileIds,
        model,
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

        // Handle iteration completion
        if (event.event_type === 'iteration_complete' && event.data) {
          // Add to local list
          const newIteration = {
            iteration: event.iteration || 0,
            thought: event.data.thought as string,
            code: event.data.code as string,
            execution_logs: event.data.execution_logs as string,
            output: event.data.output as any, // TypedData
            success: event.data.success as boolean,
            error: event.data.error as string,
          }
          iterations.push(newIteration)

          // Update message in state immediately
          setMessages(prev => prev.map(msg =>
            msg.message_id === assistantMessageId
              ? { ...msg, iterations: [...iterations] }
              : msg
          ))
        }

        // Handle completion
        if (event.type === 'completed' && event.data) {
          // Extract result - backend sends serialized result directly
          const rawResult = event.data.result

          // Convert result to displayable string
          if (rawResult !== null && rawResult !== undefined) {
            if (typeof rawResult === 'string') {
              assistantContent = rawResult
            } else if (Array.isArray(rawResult)) {
              // DataFrame converted to records - format as summary
              assistantContent = `Analysis complete. Generated ${rawResult.length} rows of data.`
            } else if (typeof rawResult === 'object') {
              // Check if it's a special type like matplotlib_figure
              const resultObj = rawResult as Record<string, unknown>
              if (resultObj.type === 'matplotlib_figure' || resultObj.type === 'plotly_figure') {
                assistantContent = 'Generated visualization.'
              } else {
                assistantContent = JSON.stringify(rawResult, null, 2)
              }
            } else {
              assistantContent = String(rawResult)
            }
          } else {
            assistantContent = event.message || 'Analysis complete.'
          }

          // Extract artifacts if available
          assistantArtifacts = event.data.artifacts as Array<{
            artifact_id: string
            url: string
            file_name: string
            file_type: string
          }> | undefined

          artifactIds = event.data.artifact_ids as string[] || []

          if (artifactIds.length > 0 && onArtifactsCreated) {
            onArtifactsCreated(artifactIds)
          }

          // Final update to message
          setMessages(prev => prev.map(msg =>
            msg.message_id === assistantMessageId
              ? {
                ...msg,
                content: assistantContent,
                artifact_ids: artifactIds,
                metadata: {
                  ...msg.metadata,
                  artifacts: assistantArtifacts
                }
              }
              : msg
          ))
        }

        // Handle errors
        if (event.type === 'error') {
          throw new Error(event.message)
        }
      }

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

      // Update the assistant message to show error state if it exists, or add new one
      setMessages(prev => {
        const exists = prev.some(m => m.message_id === assistantMessageId)
        if (exists) {
          return prev.map(msg =>
            msg.message_id === assistantMessageId
              ? { ...msg, is_error: true, content: (e as Error).message || msg.content }
              : msg
          )
        }
        return [...prev, {
          message_id: crypto.randomUUID(),
          session_id: sessionId,
          role: 'assistant',
          content: (e as Error).message,
          artifact_ids: [],
          is_error: true,
          created_at: new Date().toISOString(),
          metadata: {},
        }]
      })
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
      const rawMessages = Array.isArray(response.data)
        ? response.data
        : (response.data as any).messages || []

      const messages = rawMessages.map((msg: Message) => ({
        ...msg,
        artifact_ids: msg.artifact_ids || [],
        iterations: msg.iterations || [],
      }))

      setMessages(messages)
    }
  }, [sessionId])

  useEffect(() => {
    setMessages([])
    setError(null)
    setState({
      status: 'idle',
      currentThought: null,
      currentCode: null,
      iteration: 0,
      totalIterations: 0,
    })

    if (sessionId) {
      loadHistory()
    }
  }, [sessionId, loadHistory])

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

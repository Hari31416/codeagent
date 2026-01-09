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
      let assistantArtifacts: Array<{
        artifact_id: string
        url: string
        file_name: string
        file_type: string
      }> | undefined

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

          // Extract code and thoughts from code_history if available
          const codeHistory = event.data.code_history as Array<{
            code?: string
            thoughts?: string
            output?: unknown // Changed from string to unknown
          }> | undefined

          if (codeHistory && codeHistory.length > 0) {
            const lastEntry = codeHistory[codeHistory.length - 1]
            assistantCode = lastEntry.code
            assistantThoughts = lastEntry.thoughts

            // If we have output from the last execution, use that as content
            if (lastEntry.output && lastEntry.output !== 'No return value') {
              if (typeof lastEntry.output === 'string') {
                assistantContent = lastEntry.output
              } else {
                assistantContent = JSON.stringify(lastEntry.output, null, 2)
              }
            }
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
        metadata: {
          // Store artifact details with URLs in metadata for immediate display
          artifacts: assistantArtifacts
        },
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

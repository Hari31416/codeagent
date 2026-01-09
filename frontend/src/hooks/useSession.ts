import { useState, useEffect, useCallback } from 'react'
import * as sessionApi from '@/api/sessions'
import type { Session } from '@/types/session'
import { getUserId } from '@/lib/user'

export function useSession(sessionId?: string) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const loadSession = useCallback(async () => {
    if (!sessionId) return

    setLoading(true)
    setError(null)

    try {
      const response = await sessionApi.getSession(sessionId)
      if (response.success && response.data) {
        setSession(response.data)
      }
    } catch (e) {
      setError(e as Error)
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => {
    loadSession()
  }, [loadSession])

  const createSession = useCallback(async (projectId: string, name?: string) => {
    setLoading(true)
    try {
      const userId = getUserId()
      const response = await sessionApi.createSession({
        name,
        user_id: userId,
        project_id: projectId,
      })
      if (response.success && response.data) {
        setSession(response.data)
        return response.data
      }
      throw new Error('Failed to create session')
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    session,
    loading,
    error,
    createSession,
    refresh: loadSession,
  }
}

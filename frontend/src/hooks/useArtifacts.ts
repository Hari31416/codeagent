import { useState, useCallback, useEffect } from 'react'
import { getSessionArtifacts } from '@/api/sessions'
import type { Artifact } from '@/types/artifact'

export function useArtifacts(sessionId?: string) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const loadArtifacts = useCallback(async () => {
    if (!sessionId) return
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await getSessionArtifacts(sessionId)
      if (response.success && response.data) {
        setArtifacts(response.data)
      }
    } catch (e) {
      setError(e as Error)
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => {
    loadArtifacts()
  }, [loadArtifacts])

  return {
    artifacts,
    loading,
    error,
    refresh: loadArtifacts
  }
}

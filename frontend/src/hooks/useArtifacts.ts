import { useState, useCallback, useEffect } from 'react'
import { getSessionArtifacts } from '@/api/sessions'
import { getProjectArtifacts } from '@/api/projects'
import type { Artifact } from '@/types/artifact'

export function useArtifacts(sessionId?: string, projectId?: string) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const loadArtifacts = useCallback(async () => {
    if (!sessionId && !projectId) return
    
    setLoading(true)
    setError(null)
    
    try {
      const promises: Promise<any>[] = []

      if (sessionId) promises.push(getSessionArtifacts(sessionId))
      if (projectId) promises.push(getProjectArtifacts(projectId))

      const results = await Promise.all(promises)

      const allArtifacts: Artifact[] = []

      results.forEach(response => {
        if (response.success && response.data) {
          allArtifacts.push(...response.data)
        }
      })

      // Deduplicate by artifact_id just in case
      const uniqueArtifacts = Array.from(
        new Map(allArtifacts.map(a => [a.artifact_id, a])).values()
      )

      // Sort by creation time desc
      uniqueArtifacts.sort((a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )

      setArtifacts(uniqueArtifacts)
    } catch (e) {
      setError(e as Error)
    } finally {
      setLoading(false)
    }
  }, [sessionId, projectId])

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

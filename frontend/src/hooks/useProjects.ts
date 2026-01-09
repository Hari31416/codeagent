import { useState, useCallback, useEffect } from 'react'
import * as projectsApi from '@/api/projects'
import type { Project } from '@/types/project'
import { getUserId } from '@/lib/user'

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const loadProjects = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const userId = getUserId()
      const response = await projectsApi.getProjects(userId)
      if (response.success) {
        setProjects(response.data)
      }
    } catch (e) {
      setError(e as Error)
      console.error('Failed to load projects', e)
    } finally {
      setLoading(false)
    }
  }, [])

  const createProject = useCallback(async (name: string, description?: string) => {
    try {
      const userId = getUserId()
      const response = await projectsApi.createProject({
        user_id: userId,
        name,
        description,
      })
      if (response.success) {
        await loadProjects()
        return response.data
      }
      return null
    } catch (e) {
      console.error('Failed to create project', e)
      return null
    }
  }, [loadProjects])

  const updateProject = useCallback(async (
    projectId: string,
    updates: { name?: string; description?: string }
  ) => {
    try {
      const response = await projectsApi.updateProject(projectId, updates)
      if (response.success) {
        await loadProjects()
        return response.data
      }
      return null
    } catch (e) {
      console.error('Failed to update project', e)
      return null
    }
  }, [loadProjects])

  const deleteProject = useCallback(async (projectId: string) => {
    try {
      await projectsApi.deleteProject(projectId)
      await loadProjects()
      if (selectedProjectId === projectId) {
        setSelectedProjectId(null)
      }
      return true
    } catch (e) {
      console.error('Failed to delete project', e)
      return false
    }
  }, [loadProjects, selectedProjectId])

  const selectProject = useCallback((projectId: string | null) => {
    setSelectedProjectId(projectId)
  }, [])

  useEffect(() => {
    loadProjects()
  }, [loadProjects])

  return {
    projects,
    selectedProjectId,
    selectedProject: projects.find(p => p.project_id === selectedProjectId) ?? null,
    loading,
    error,
    createProject,
    updateProject,
    deleteProject,
    selectProject,
    refreshProjects: loadProjects,
  }
}

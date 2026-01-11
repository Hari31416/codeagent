import { apiRequest, handleAuthError } from './client'
import type { Project, CreateProjectRequest, ProjectListResponse } from '@/types/project'
import type { ApiResponse } from '@/types/api'
import type { Artifact, UploadResponse } from '@/types/artifact'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8011/api/v1'

export async function createProject(
  request: CreateProjectRequest
): Promise<ApiResponse<Project>> {
  return apiRequest('/projects', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export async function getProjects(): Promise<ProjectListResponse> {
  return apiRequest('/projects')
}

export async function getProject(projectId: string): Promise<ApiResponse<Project>> {
  return apiRequest(`/projects/${projectId}`)
}

export async function updateProject(
  projectId: string,
  updates: { name?: string; description?: string }
): Promise<ApiResponse<Project>> {
  return apiRequest(`/projects/${projectId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })
}

export async function deleteProject(projectId: string): Promise<ApiResponse<void>> {
  return apiRequest(`/projects/${projectId}`, { method: 'DELETE' })
}

export async function getProjectArtifacts(projectId: string): Promise<ApiResponse<Artifact[]>> {
  return apiRequest(`/artifacts/projects/${projectId}`)
}

export async function uploadProjectFile(
  projectId: string,
  file: File
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  // Use fetch directly for FormData to avoid Content-Type header issues with apiRequest wrapper
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    },
    body: formData,
  })

  if (!response.ok) {
    handleAuthError(response.status)
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(error.detail || 'Upload failed')
  }

  return response.json()
}

export async function exportProject(projectId: string): Promise<ApiResponse<import('@/types/api').ExportData>> {
  return apiRequest(`/projects/${projectId}/export`)
}

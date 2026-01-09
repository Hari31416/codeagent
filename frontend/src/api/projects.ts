import { apiRequest } from './client'
import type { Project, CreateProjectRequest, ProjectListResponse } from '@/types/project'
import type { ApiResponse } from '@/types/api'
import type { Artifact, UploadResponse } from '@/types/artifact'

export async function createProject(
  request: CreateProjectRequest
): Promise<ApiResponse<Project>> {
  return apiRequest('/projects', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export async function getProjects(userId: string): Promise<ProjectListResponse> {
  return apiRequest(`/projects?user_id=${userId}`)
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
  // assuming apiRequest adds JSON headers
  const token = localStorage.getItem('token')
  const headers: HeadersInit = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  const response = await fetch(`/api/v1/projects/${projectId}/upload`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(error.detail || 'Upload failed')
  }

  return response.json()
}

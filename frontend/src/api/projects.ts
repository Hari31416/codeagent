import { apiRequest } from './client'
import type { Project, CreateProjectRequest, ProjectListResponse } from '@/types/project'
import type { ApiResponse } from '@/types/api'

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

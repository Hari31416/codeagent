import { apiRequest } from './client'
import type { Session, CreateSessionRequest, SessionListResponse } from '@/types/session'
import type { ChatHistory } from '@/types/message'
import type { ApiResponse } from '@/types/api'
import type { Artifact } from '@/types/artifact'

export async function createSession(
  request?: CreateSessionRequest
): Promise<ApiResponse<Session>> {
  return apiRequest('/sessions', {
    method: 'POST',
    body: JSON.stringify(request || {}),
  })
}

export async function updateSession(
  sessionId: string,
  updates: { name?: string }
): Promise<ApiResponse<Session>> {
  return apiRequest(`/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })
}

export async function getSessions(
  projectId?: string
): Promise<SessionListResponse> {
  let url = '/sessions'
  if (projectId) {
    url += `?project_id=${projectId}`
  }
  return apiRequest(url)
}

export async function getSession(sessionId: string): Promise<ApiResponse<Session>> {
  return apiRequest(`/sessions/${sessionId}`)
}

export async function getSessionHistory(
  sessionId: string,
  limit = 100,
  offset = 0
): Promise<ApiResponse<ChatHistory>> {
  return apiRequest(`/sessions/${sessionId}/history?limit=${limit}&offset=${offset}`)
}

export async function deleteSession(sessionId: string): Promise<ApiResponse<void>> {
  return apiRequest(`/sessions/${sessionId}`, { method: 'DELETE' })
}

export async function getSessionArtifacts(sessionId: string): Promise<ApiResponse<Artifact[]>> {
  return apiRequest(`/sessions/${sessionId}/artifacts`)
}

export async function exportSession(sessionId: string): Promise<ApiResponse<import('@/types/api').ExportData>> {
  return apiRequest(`/sessions/${sessionId}/export`)
}

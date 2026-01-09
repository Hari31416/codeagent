export interface Session {
  session_id: string
  project_id: string
  name: string | null
  created_at: string
  updated_at: string
  metadata: Record<string, unknown>
}

export interface CreateSessionRequest {
  name?: string
  user_id?: string
  project_id: string
}

export interface SessionListResponse {
  success: boolean
  data: Session[]
}


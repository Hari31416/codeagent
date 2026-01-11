export interface Project {
  project_id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
  metadata: Record<string, unknown>
}

export interface CreateProjectRequest {
  name: string
  description?: string
}

export interface ProjectListResponse {
  success: boolean
  data: Project[]
}

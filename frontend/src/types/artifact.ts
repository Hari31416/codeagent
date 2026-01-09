export type ArtifactType = 
  | 'csv' 
  | 'xlsx' 
  | 'xls'
  | 'png' 
  | 'jpg' 
  | 'jpeg' 
  | 'gif'
  | 'json' 
  | 'py' 
  | 'md' 
  | 'txt' 
  | 'html'
  | 'unknown'

export interface Artifact {
  artifact_id: string
  session_id: string
  file_name: string
  file_type: ArtifactType
  mime_type: string
  size_bytes: number
  presigned_url?: string
  created_at: string
  metadata: Record<string, unknown>
}

export interface UploadResponse {
  success: boolean
  data: {
    artifact_id: string
    file_name: string
    file_type: string
    size_bytes: number
    presigned_url: string
  }
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

export type StreamEventType = 
  | 'started'
  | 'thinking'
  | 'generating_code'
  | 'executing'
  | 'iteration_complete'
  | 'error'
  | 'completed'
  | 'completed'
  | 'cancelled'

export type TypedDataKind = 'text' | 'table' | 'image' | 'plotly' | 'json' | 'multi'

export interface TypedData {
  kind: TypedDataKind
  data: unknown
  metadata?: Record<string, unknown>
}

export interface IterationOutput {
  iteration: number
  thought?: string
  thoughts?: string
  code?: string
  execution_logs?: string
  output?: TypedData
  artifacts?: Array<{
    artifact_id: string
    file_name: string
    file_type: string
    url: string
  }>
  success: boolean
  error?: string
}

export interface StreamEvent {
  type: 'status' | 'completed' | 'error' | 'cancelled'
  event_type: StreamEventType
  agent_name: string
  message: string
  data?: Record<string, unknown>
  iteration?: number
  total_iterations?: number
  timestamp: string
}

export interface QueryRequest {
  query: string
  file_ids?: string[]
  model?: string
}

export interface ModelInfo {
  id: string
  name: string
  provider: string
  slug: string
  context_length: number
  description?: string
}

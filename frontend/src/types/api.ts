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
  | 'cancelled'

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
}

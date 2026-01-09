export type MessageRole = 'user' | 'assistant' | 'system'

export interface Message {
  message_id: string
  session_id: string
  role: MessageRole
  content: string
  code?: string
  thoughts?: string
  artifact_ids: string[]
  execution_logs?: string
  is_error: boolean
  created_at: string
  metadata: Record<string, unknown>
  iterations?: import('./api').IterationOutput[]
}

export interface ChatHistory {
  messages: Message[]
  hasMore: boolean
  total: number
}

# Frontend Implementation Guide

This document provides detailed instructions for implementing the AI Coding & Data Analysis Agent frontend as described in `overview.md`.

---

## Table of Contents

1. [Existing Setup Overview](#existing-setup-overview)
2. [Project Structure](#project-structure)
3. [Phase 3: Frontend & Visualization](#phase-3-frontend--visualization)
4. [Component Implementation](#component-implementation)
5. [State Management](#state-management)
6. [API Integration](#api-integration)
7. [Styling Guidelines](#styling-guidelines)

---

## Existing Setup Overview

The frontend is already initialized with:

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19.2.0 | UI framework |
| Vite | 7.2.4 | Build tool |
| TypeScript | 5.9.3 | Type safety |
| Tailwind CSS | 4.1.17 | Styling |
| shadcn/ui | 3.6.3 | Component library |
| Lucide React | 0.562.0 | Icons |
| radix-ui | 1.4.3 | Headless UI primitives |

### Existing UI Components (in `src/components/ui/`)

- `alert-dialog.tsx` - Modal dialogs
- `badge.tsx` - Status badges
- `button.tsx` - Button variants
- `card.tsx` - Card containers
- `combobox.tsx` - Searchable dropdowns
- `dropdown-menu.tsx` - Context menus
- `field.tsx` - Form fields
- `input-group.tsx` - Input with addons
- `input.tsx` - Text inputs
- `label.tsx` - Form labels
- `select.tsx` - Select dropdowns
- `separator.tsx` - Visual dividers
- `textarea.tsx` - Multiline input

---

## Project Structure

Recommended structure for implementation:

```
frontend/src/
├── api/                      # API client and hooks
│   ├── client.ts             # Axios/fetch client
│   ├── sessions.ts           # Session API calls
│   ├── upload.ts             # File upload API
│   └── query.ts              # Query/SSE handling
│
├── components/
│   ├── ui/                   # Existing shadcn components
│   │
│   ├── chat/                 # Chat interface components
│   │   ├── ChatContainer.tsx
│   │   ├── ChatInput.tsx
│   │   ├── MessageList.tsx
│   │   ├── Message.tsx
│   │   └── TypingIndicator.tsx
│   │
│   ├── artifacts/            # Artifact display components
│   │   ├── ArtifactCard.tsx
│   │   ├── ArtifactRenderer.tsx
│   │   ├── ImageArtifact.tsx
│   │   ├── TableArtifact.tsx
│   │   ├── MarkdownArtifact.tsx
│   │   └── CodeViewer.tsx
│   │
│   ├── upload/               # File upload components
│   │   ├── FileUpload.tsx
│   │   ├── FileList.tsx
│   │   └── UploadProgress.tsx
│   │
│   ├── session/              # Session management
│   │   ├── SessionSidebar.tsx
│   │   ├── SessionList.tsx
│   │   └── NewSessionDialog.tsx
│   │
│   └── layout/               # Layout components
│       ├── MainLayout.tsx
│       ├── Header.tsx
│       └── Sidebar.tsx
│
├── hooks/                    # Custom React hooks
│   ├── useSession.ts
│   ├── useChat.ts
│   ├── useArtifacts.ts
│   ├── useSSE.ts
│   └── useFileUpload.ts
│
├── stores/                   # State management
│   ├── sessionStore.ts
│   ├── chatStore.ts
│   └── artifactStore.ts
│
├── types/                    # TypeScript types
│   ├── session.ts
│   ├── message.ts
│   ├── artifact.ts
│   └── api.ts
│
├── lib/                      # Utilities
│   └── utils.ts              # Existing utility functions
│
├── App.tsx                   # Main app component
├── main.tsx                  # Entry point
└── index.css                 # Global styles
```

---

## Phase 3: Frontend & Visualization

### 3.1 Type Definitions

Create: `src/types/session.ts`

```typescript
export interface Session {
  session_id: string
  name: string | null
  created_at: string
  updated_at: string
  metadata: Record<string, unknown>
}

export interface CreateSessionRequest {
  name?: string
}

export interface SessionListResponse {
  success: boolean
  data: Session[]
}
```

Create: `src/types/message.ts`

```typescript
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
}

export interface ChatHistory {
  messages: Message[]
  hasMore: boolean
  total: number
}
```

Create: `src/types/artifact.ts`

```typescript
export type ArtifactType = 
  | 'csv' 
  | 'xlsx' 
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
```

Create: `src/types/api.ts`

```typescript
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
```

### 3.2 API Client

Create: `src/api/client.ts`

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8011/api/v1'

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }))
    throw new Error(error.error || error.message || 'Request failed')
  }

  return response.json()
}

export function createSSEConnection(
  endpoint: string,
  onEvent: (event: StreamEvent) => void,
  onError: (error: Error) => void
): EventSource {
  const url = `${API_BASE_URL}${endpoint}`
  const eventSource = new EventSource(url)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as StreamEvent
      onEvent(data)
    } catch (e) {
      console.error('Failed to parse SSE event:', e)
    }
  }

  eventSource.onerror = (event) => {
    console.error('SSE error:', event)
    onError(new Error('Connection lost'))
    eventSource.close()
  }

  return eventSource
}
```

Create: `src/api/sessions.ts`

```typescript
import { apiRequest } from './client'
import type { Session, CreateSessionRequest, SessionListResponse } from '@/types/session'
import type { ChatHistory } from '@/types/message'
import type { ApiResponse } from '@/types/api'

export async function createSession(
  request?: CreateSessionRequest
): Promise<ApiResponse<Session>> {
  return apiRequest('/sessions', {
    method: 'POST',
    body: JSON.stringify(request || {}),
  })
}

export async function getSessions(): Promise<SessionListResponse> {
  return apiRequest('/sessions')
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
```

Create: `src/api/upload.ts`

```typescript
import type { UploadResponse } from '@/types/artifact'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8011/api/v1'

export async function uploadFile(
  sessionId: string,
  file: File,
  onProgress?: (progress: number) => void
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const formData = new FormData()
    formData.append('file', file)

    const xhr = new XMLHttpRequest()
    
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        const progress = Math.round((event.loaded / event.total) * 100)
        onProgress(progress)
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText))
      } else {
        reject(new Error(`Upload failed: ${xhr.statusText}`))
      }
    })

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed'))
    })

    xhr.open('POST', `${API_BASE_URL}/sessions/${sessionId}/upload`)
    xhr.send(formData)
  })
}
```

Create: `src/api/query.ts`

```typescript
import type { QueryRequest, StreamEvent } from '@/types/api'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8011/api/v1'

export async function* streamQuery(
  sessionId: string,
  request: QueryRequest
): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await fetch(
    `${API_BASE_URL}/sessions/${sessionId}/query`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(request),
    }
  )

  if (!response.ok) {
    throw new Error(`Query failed: ${response.statusText}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('No response body')
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    
    // Keep the last potentially incomplete line in the buffer
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const jsonStr = line.slice(6).trim()
        if (jsonStr) {
          try {
            yield JSON.parse(jsonStr) as StreamEvent
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    }
  }
}
```

### 3.3 Custom Hooks

Create: `src/hooks/useSession.ts`

```typescript
import { useState, useEffect, useCallback } from 'react'
import * as sessionApi from '@/api/sessions'
import type { Session } from '@/types/session'

export function useSession(sessionId?: string) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const loadSession = useCallback(async () => {
    if (!sessionId) return
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await sessionApi.getSession(sessionId)
      if (response.success && response.data) {
        setSession(response.data)
      }
    } catch (e) {
      setError(e as Error)
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => {
    loadSession()
  }, [loadSession])

  const createSession = useCallback(async (name?: string) => {
    setLoading(true)
    try {
      const response = await sessionApi.createSession({ name })
      if (response.success && response.data) {
        setSession(response.data)
        return response.data
      }
      throw new Error('Failed to create session')
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    session,
    loading,
    error,
    createSession,
    refresh: loadSession,
  }
}
```

Create: `src/hooks/useChat.ts`

```typescript
import { useState, useCallback, useRef } from 'react'
import { streamQuery } from '@/api/query'
import type { Message } from '@/types/message'
import type { StreamEvent, StreamEventType } from '@/types/api'

interface UseChatOptions {
  sessionId: string
  onArtifactsCreated?: (artifactIds: string[]) => void
}

interface ChatState {
  status: StreamEventType | 'idle'
  currentThought: string | null
  currentCode: string | null
  iteration: number
  totalIterations: number
}

export function useChat({ sessionId, onArtifactsCreated }: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([])
  const [state, setState] = useState<ChatState>({
    status: 'idle',
    currentThought: null,
    currentCode: null,
    iteration: 0,
    totalIterations: 0,
  })
  const [error, setError] = useState<Error | null>(null)
  
  const abortControllerRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(async (
    content: string,
    fileIds?: string[]
  ) => {
    if (!sessionId) return

    // Add user message immediately
    const userMessage: Message = {
      message_id: crypto.randomUUID(),
      session_id: sessionId,
      role: 'user',
      content,
      artifact_ids: fileIds || [],
      is_error: false,
      created_at: new Date().toISOString(),
      metadata: {},
    }
    
    setMessages(prev => [...prev, userMessage])
    setError(null)
    setState(prev => ({ ...prev, status: 'started' }))

    try {
      let assistantContent = ''
      let assistantCode: string | undefined
      let assistantThoughts: string | undefined
      let artifactIds: string[] = []

      for await (const event of streamQuery(sessionId, {
        query: content,
        file_ids: fileIds,
      })) {
        // Update state based on event
        setState(prev => ({
          ...prev,
          status: event.event_type,
          iteration: event.iteration || prev.iteration,
          totalIterations: event.total_iterations || prev.totalIterations,
          currentThought: event.event_type === 'thinking' 
            ? event.message 
            : prev.currentThought,
          currentCode: event.event_type === 'generating_code' && event.data?.code
            ? event.data.code as string
            : prev.currentCode,
        }))

        // Handle completion
        if (event.type === 'completed' && event.data) {
          assistantContent = (event.data.result as Record<string, unknown>)?.answer as string || event.message
          assistantCode = (event.data.result as Record<string, unknown>)?.code as string | undefined
          assistantThoughts = (event.data.result as Record<string, unknown>)?.thoughts as string | undefined
          artifactIds = event.data.artifact_ids as string[] || []
          
          if (artifactIds.length > 0 && onArtifactsCreated) {
            onArtifactsCreated(artifactIds)
          }
        }

        // Handle errors
        if (event.type === 'error') {
          throw new Error(event.message)
        }
      }

      // Add assistant message
      const assistantMessage: Message = {
        message_id: crypto.randomUUID(),
        session_id: sessionId,
        role: 'assistant',
        content: assistantContent,
        code: assistantCode,
        thoughts: assistantThoughts,
        artifact_ids: artifactIds,
        is_error: false,
        created_at: new Date().toISOString(),
        metadata: {},
      }
      
      setMessages(prev => [...prev, assistantMessage])
      setState({
        status: 'idle',
        currentThought: null,
        currentCode: null,
        iteration: 0,
        totalIterations: 0,
      })

    } catch (e) {
      setError(e as Error)
      setState(prev => ({ ...prev, status: 'error' }))
      
      // Add error message
      setMessages(prev => [...prev, {
        message_id: crypto.randomUUID(),
        session_id: sessionId,
        role: 'assistant',
        content: (e as Error).message,
        artifact_ids: [],
        is_error: true,
        created_at: new Date().toISOString(),
        metadata: {},
      }])
    }
  }, [sessionId, onArtifactsCreated])

  const cancelQuery = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      setState(prev => ({ ...prev, status: 'cancelled' }))
    }
  }, [])

  const loadHistory = useCallback(async () => {
    if (!sessionId) return
    
    const response = await sessionApi.getSessionHistory(sessionId)
    if (response.success && response.data) {
      setMessages(response.data.messages)
    }
  }, [sessionId])

  return {
    messages,
    state,
    error,
    sendMessage,
    cancelQuery,
    loadHistory,
    isProcessing: state.status !== 'idle' && state.status !== 'error',
  }
}

// Import statement for sessionApi (add at top)
import * as sessionApi from '@/api/sessions'
```

Create: `src/hooks/useFileUpload.ts`

```typescript
import { useState, useCallback } from 'react'
import { uploadFile } from '@/api/upload'
import type { Artifact } from '@/types/artifact'

interface UploadState {
  isUploading: boolean
  progress: number
  error: Error | null
}

export function useFileUpload(sessionId: string) {
  const [state, setState] = useState<UploadState>({
    isUploading: false,
    progress: 0,
    error: null,
  })
  const [uploadedFiles, setUploadedFiles] = useState<Artifact[]>([])

  const upload = useCallback(async (files: File[]): Promise<Artifact[]> => {
    setState({ isUploading: true, progress: 0, error: null })
    
    const artifacts: Artifact[] = []
    
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        
        const response = await uploadFile(
          sessionId,
          file,
          (progress) => {
            // Calculate overall progress across all files
            const overallProgress = ((i / files.length) + (progress / 100 / files.length)) * 100
            setState(prev => ({ ...prev, progress: Math.round(overallProgress) }))
          }
        )
        
        if (response.success && response.data) {
          const artifact: Artifact = {
            artifact_id: response.data.artifact_id,
            session_id: sessionId,
            file_name: response.data.file_name,
            file_type: response.data.file_type as Artifact['file_type'],
            mime_type: 'application/octet-stream',
            size_bytes: response.data.size_bytes,
            presigned_url: response.data.presigned_url,
            created_at: new Date().toISOString(),
            metadata: {},
          }
          artifacts.push(artifact)
        }
      }
      
      setUploadedFiles(prev => [...prev, ...artifacts])
      setState({ isUploading: false, progress: 100, error: null })
      
      return artifacts
      
    } catch (e) {
      setState({ isUploading: false, progress: 0, error: e as Error })
      throw e
    }
  }, [sessionId])

  const clearUploads = useCallback(() => {
    setUploadedFiles([])
  }, [])

  return {
    ...state,
    uploadedFiles,
    upload,
    clearUploads,
  }
}
```

---

## Component Implementation

### 4.1 Chat Interface

Create: `src/components/chat/ChatContainer.tsx`

```tsx
import { useCallback, useState } from 'react'
import { useChat } from '@/hooks/useChat'
import { useFileUpload } from '@/hooks/useFileUpload'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { TypingIndicator } from './TypingIndicator'
import { FileUpload } from '@/components/upload/FileUpload'
import { FileList } from '@/components/upload/FileList'

interface ChatContainerProps {
  sessionId: string
  onArtifactSelect?: (artifactId: string) => void
}

export function ChatContainer({ sessionId, onArtifactSelect }: ChatContainerProps) {
  const [attachedFileIds, setAttachedFileIds] = useState<string[]>([])
  
  const { 
    messages, 
    state, 
    sendMessage, 
    isProcessing,
    loadHistory 
  } = useChat({
    sessionId,
    onArtifactsCreated: (ids) => {
      // Optionally auto-select first artifact
      if (ids.length > 0 && onArtifactSelect) {
        onArtifactSelect(ids[0])
      }
    },
  })
  
  const { 
    isUploading, 
    progress, 
    uploadedFiles, 
    upload,
    clearUploads 
  } = useFileUpload(sessionId)

  const handleSend = useCallback(async (content: string) => {
    await sendMessage(content, attachedFileIds)
    setAttachedFileIds([])
    clearUploads()
  }, [sendMessage, attachedFileIds, clearUploads])

  const handleFilesSelected = useCallback(async (files: File[]) => {
    const artifacts = await upload(files)
    setAttachedFileIds(prev => [...prev, ...artifacts.map(a => a.artifact_id)])
  }, [upload])

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        <MessageList 
          messages={messages} 
          onArtifactClick={onArtifactSelect}
        />
        
        {isProcessing && (
          <TypingIndicator
            status={state.status}
            thought={state.currentThought}
            iteration={state.iteration}
            totalIterations={state.totalIterations}
          />
        )}
      </div>

      {/* Attached files preview */}
      {uploadedFiles.length > 0 && (
        <div className="px-4 py-2 border-t">
          <FileList 
            files={uploadedFiles} 
            onRemove={(id) => {
              setAttachedFileIds(prev => prev.filter(fid => fid !== id))
            }}
          />
        </div>
      )}

      {/* Input area */}
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <FileUpload 
            onFilesSelected={handleFilesSelected}
            isUploading={isUploading}
            progress={progress}
          />
          <ChatInput 
            onSend={handleSend}
            disabled={isProcessing || isUploading}
            placeholder={isProcessing ? 'Processing...' : 'Ask about your data...'}
          />
        </div>
      </div>
    </div>
  )
}
```

Create: `src/components/chat/ChatInput.tsx`

```tsx
import { useState, useCallback, KeyboardEvent } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Send } from 'lucide-react'

interface ChatInputProps {
  onSend: (content: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
  const [value, setValue] = useState('')

  const handleSend = useCallback(() => {
    const trimmed = value.trim()
    if (trimmed && !disabled) {
      onSend(trimmed)
      setValue('')
    }
  }, [value, onSend, disabled])

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend])

  return (
    <div className="flex gap-2 flex-1">
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || 'Type your message...'}
        disabled={disabled}
        className="min-h-[44px] max-h-[200px] resize-none"
        rows={1}
      />
      <Button 
        onClick={handleSend} 
        disabled={disabled || !value.trim()}
        size="icon"
      >
        <Send className="h-4 w-4" />
      </Button>
    </div>
  )
}
```

Create: `src/components/chat/MessageList.tsx`

```tsx
import { useRef, useEffect } from 'react'
import type { Message as MessageType } from '@/types/message'
import { Message } from './Message'

interface MessageListProps {
  messages: MessageType[]
  onArtifactClick?: (artifactId: string) => void
}

export function MessageList({ messages, onArtifactClick }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
        <p className="text-lg">Start a conversation</p>
        <p className="text-sm">Upload a file or ask a question to get started</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <Message 
          key={message.message_id} 
          message={message}
          onArtifactClick={onArtifactClick}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
```

Create: `src/components/chat/Message.tsx`

```tsx
import { cn } from '@/lib/utils'
import type { Message as MessageType } from '@/types/message'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CodeViewer } from '@/components/artifacts/CodeViewer'
import { User, Bot, AlertCircle } from 'lucide-react'

interface MessageProps {
  message: MessageType
  onArtifactClick?: (artifactId: string) => void
}

export function Message({ message, onArtifactClick }: MessageProps) {
  const isUser = message.role === 'user'
  const isError = message.is_error

  return (
    <div className={cn(
      'flex gap-3',
      isUser ? 'flex-row-reverse' : 'flex-row'
    )}>
      {/* Avatar */}
      <div className={cn(
        'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
        isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
      )}>
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Content */}
      <div className={cn(
        'flex flex-col gap-2 max-w-[80%]',
        isUser ? 'items-end' : 'items-start'
      )}>
        {/* Thoughts (for assistant messages) */}
        {message.thoughts && !isUser && (
          <Card className="p-3 bg-muted/50 text-sm text-muted-foreground">
            <p className="font-medium mb-1">Thinking:</p>
            <p>{message.thoughts}</p>
          </Card>
        )}

        {/* Main content */}
        <Card className={cn(
          'p-3',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-card',
          isError && 'border-destructive bg-destructive/10'
        )}>
          {isError && (
            <div className="flex items-center gap-2 text-destructive mb-2">
              <AlertCircle className="h-4 w-4" />
              <span className="font-medium">Error</span>
            </div>
          )}
          <p className="whitespace-pre-wrap">{message.content}</p>
        </Card>

        {/* Code block */}
        {message.code && !isUser && (
          <CodeViewer code={message.code} language="python" />
        )}

        {/* Artifact badges */}
        {message.artifact_ids.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {message.artifact_ids.map((id) => (
              <Badge
                key={id}
                variant="outline"
                className="cursor-pointer hover:bg-accent"
                onClick={() => onArtifactClick?.(id)}
              >
                View Artifact
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
```

Create: `src/components/chat/TypingIndicator.tsx`

```tsx
import { Card } from '@/components/ui/card'
import { Bot, Brain, Code, Play, Check } from 'lucide-react'
import type { StreamEventType } from '@/types/api'

interface TypingIndicatorProps {
  status: StreamEventType | 'idle'
  thought?: string | null
  iteration?: number
  totalIterations?: number
}

const statusConfig: Record<StreamEventType, { icon: React.ElementType; label: string }> = {
  started: { icon: Bot, label: 'Starting...' },
  thinking: { icon: Brain, label: 'Thinking...' },
  generating_code: { icon: Code, label: 'Writing code...' },
  executing: { icon: Play, label: 'Executing...' },
  iteration_complete: { icon: Check, label: 'Iteration complete' },
  completed: { icon: Check, label: 'Done' },
  error: { icon: Bot, label: 'Error' },
  cancelled: { icon: Bot, label: 'Cancelled' },
}

export function TypingIndicator({ 
  status, 
  thought,
  iteration,
  totalIterations 
}: TypingIndicatorProps) {
  if (status === 'idle') return null

  const config = statusConfig[status as StreamEventType] || statusConfig.started
  const Icon = config.icon

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center animate-pulse">
        <Bot className="h-4 w-4" />
      </div>

      <Card className="p-3 max-w-[80%]">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Icon className="h-4 w-4 animate-spin" />
          <span>{config.label}</span>
          {iteration !== undefined && totalIterations !== undefined && totalIterations > 0 && (
            <span className="text-xs">
              (Iteration {iteration}/{totalIterations})
            </span>
          )}
        </div>
        
        {thought && status === 'thinking' && (
          <p className="mt-2 text-sm italic">{thought}</p>
        )}
      </Card>
    </div>
  )
}
```

### 4.2 Artifact Components

Create: `src/components/artifacts/ArtifactCard.tsx`

```tsx
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { Artifact } from '@/types/artifact'
import { FileImage, FileSpreadsheet, FileCode, FileText, File } from 'lucide-react'

interface ArtifactCardProps {
  artifact: Artifact
  onClick?: () => void
  isSelected?: boolean
}

const typeIcons: Record<string, React.ElementType> = {
  png: FileImage,
  jpg: FileImage,
  jpeg: FileImage,
  gif: FileImage,
  csv: FileSpreadsheet,
  xlsx: FileSpreadsheet,
  xls: FileSpreadsheet,
  py: FileCode,
  json: FileCode,
  md: FileText,
  txt: FileText,
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

export function ArtifactCard({ artifact, onClick, isSelected }: ArtifactCardProps) {
  const Icon = typeIcons[artifact.file_type] || File

  return (
    <Card
      className={`p-3 cursor-pointer transition-all hover:shadow-md ${
        isSelected ? 'ring-2 ring-primary' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-md bg-muted">
          <Icon className="h-5 w-5 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{artifact.file_name}</p>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="secondary" className="text-xs">
              {artifact.file_type.toUpperCase()}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {formatBytes(artifact.size_bytes)}
            </span>
          </div>
        </div>
      </div>
    </Card>
  )
}
```

Create: `src/components/artifacts/ArtifactRenderer.tsx`

```tsx
import { useState, useEffect } from 'react'
import type { Artifact } from '@/types/artifact'
import { ImageArtifact } from './ImageArtifact'
import { TableArtifact } from './TableArtifact'
import { CodeViewer } from './CodeViewer'
import { MarkdownArtifact } from './MarkdownArtifact'
import { Card } from '@/components/ui/card'
import { Loader2 } from 'lucide-react'

interface ArtifactRendererProps {
  artifact: Artifact
}

export function ArtifactRenderer({ artifact }: ArtifactRendererProps) {
  const [content, setContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!artifact.presigned_url) {
      setError(new Error('No URL available'))
      setLoading(false)
      return
    }

    // For images, we don't need to fetch content
    if (['png', 'jpg', 'jpeg', 'gif'].includes(artifact.file_type)) {
      setLoading(false)
      return
    }

    // Fetch text content for other types
    fetch(artifact.presigned_url)
      .then(res => res.text())
      .then(text => {
        setContent(text)
        setLoading(false)
      })
      .catch(err => {
        setError(err)
        setLoading(false)
      })
  }, [artifact])

  if (loading) {
    return (
      <Card className="p-8 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-4 text-destructive">
        Failed to load artifact: {error.message}
      </Card>
    )
  }

  // Render based on file type
  switch (artifact.file_type) {
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif':
      return <ImageArtifact src={artifact.presigned_url!} alt={artifact.file_name} />
    
    case 'csv':
    case 'xlsx':
    case 'xls':
      return <TableArtifact content={content!} fileType={artifact.file_type} />
    
    case 'py':
      return <CodeViewer code={content!} language="python" />
    
    case 'json':
      return <CodeViewer code={content!} language="json" />
    
    case 'md':
      return <MarkdownArtifact content={content!} />
    
    case 'html':
      return (
        <Card className="p-4">
          <iframe 
            srcDoc={content!} 
            className="w-full h-[600px] border-0"
            sandbox="allow-scripts"
          />
        </Card>
      )
    
    default:
      return (
        <Card className="p-4">
          <pre className="whitespace-pre-wrap text-sm">{content}</pre>
        </Card>
      )
  }
}
```

Create: `src/components/artifacts/ImageArtifact.tsx`

```tsx
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Download, ZoomIn, ZoomOut } from 'lucide-react'
import { useState } from 'react'

interface ImageArtifactProps {
  src: string
  alt: string
}

export function ImageArtifact({ src, alt }: ImageArtifactProps) {
  const [zoom, setZoom] = useState(1)

  const handleDownload = () => {
    const link = document.createElement('a')
    link.href = src
    link.download = alt
    link.click()
  }

  return (
    <Card className="p-4">
      <div className="flex justify-end gap-2 mb-4">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setZoom(z => Math.max(0.25, z - 0.25))}
        >
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          onClick={() => setZoom(z => Math.min(3, z + 0.25))}
        >
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="icon" onClick={handleDownload}>
          <Download className="h-4 w-4" />
        </Button>
      </div>
      <div className="overflow-auto max-h-[600px]">
        <img
          src={src}
          alt={alt}
          style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}
          className="max-w-full transition-transform"
        />
      </div>
    </Card>
  )
}
```

Create: `src/components/artifacts/TableArtifact.tsx`

```tsx
import { useMemo } from 'react'
import { Card } from '@/components/ui/card'

interface TableArtifactProps {
  content: string
  fileType: 'csv' | 'xlsx' | 'xls'
}

function parseCSV(content: string): { headers: string[]; rows: string[][] } {
  const lines = content.trim().split('\n')
  if (lines.length === 0) return { headers: [], rows: [] }
  
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
  const rows = lines.slice(1).map(line => 
    line.split(',').map(cell => cell.trim().replace(/^"|"$/g, ''))
  )
  
  return { headers, rows }
}

export function TableArtifact({ content, fileType }: TableArtifactProps) {
  const { headers, rows } = useMemo(() => {
    if (fileType === 'csv') {
      return parseCSV(content)
    }
    // For Excel files, would need a proper parser
    // For now, assume content is already converted to CSV
    return parseCSV(content)
  }, [content, fileType])

  if (headers.length === 0) {
    return (
      <Card className="p-4 text-muted-foreground">
        No data to display
      </Card>
    )
  }

  return (
    <Card className="overflow-auto max-h-[500px]">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-muted">
          <tr>
            {headers.map((header, i) => (
              <th 
                key={i} 
                className="px-4 py-2 text-left font-medium border-b"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 100).map((row, i) => (
            <tr key={i} className="hover:bg-muted/50">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2 border-b whitespace-nowrap">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 100 && (
        <div className="p-2 text-center text-sm text-muted-foreground">
          Showing first 100 of {rows.length} rows
        </div>
      )}
    </Card>
  )
}
```

Create: `src/components/artifacts/CodeViewer.tsx`

```tsx
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Check, Copy } from 'lucide-react'
import { useState, useCallback } from 'react'

interface CodeViewerProps {
  code: string
  language?: string
}

export function CodeViewer({ code, language = 'python' }: CodeViewerProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [code])

  return (
    <Card className="relative">
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted">
        <span className="text-xs font-mono text-muted-foreground">
          {language}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={handleCopy}
        >
          {copied ? (
            <Check className="h-3 w-3 text-green-500" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
        </Button>
      </div>
      <pre className="p-4 overflow-auto max-h-[400px] text-sm">
        <code className="font-mono">{code}</code>
      </pre>
    </Card>
  )
}
```

Create: `src/components/artifacts/MarkdownArtifact.tsx`

```tsx
import { Card } from '@/components/ui/card'

interface MarkdownArtifactProps {
  content: string
}

export function MarkdownArtifact({ content }: MarkdownArtifactProps) {
  // For a full implementation, use a markdown parser like 'marked' or 'react-markdown'
  // This is a simple fallback
  return (
    <Card className="p-4 prose prose-sm max-w-none dark:prose-invert">
      <pre className="whitespace-pre-wrap">{content}</pre>
    </Card>
  )
}
```

### 4.3 File Upload Components

Create: `src/components/upload/FileUpload.tsx`

```tsx
import { useCallback, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Paperclip, Loader2 } from 'lucide-react'

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void
  isUploading?: boolean
  progress?: number
  accept?: string
}

export function FileUpload({ 
  onFilesSelected, 
  isUploading, 
  progress = 0,
  accept = '.csv,.xlsx,.xls,.json,.png,.jpg,.jpeg,.gif,.py,.md,.txt'
}: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleClick = useCallback(() => {
    inputRef.current?.click()
  }, [])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length > 0) {
      onFilesSelected(files)
    }
    // Reset input
    e.target.value = ''
  }, [onFilesSelected])

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={accept}
        onChange={handleChange}
        className="hidden"
      />
      <Button
        variant="outline"
        size="icon"
        onClick={handleClick}
        disabled={isUploading}
      >
        {isUploading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Paperclip className="h-4 w-4" />
        )}
      </Button>
      {isUploading && progress > 0 && (
        <span className="text-xs text-muted-foreground">
          {progress}%
        </span>
      )}
    </>
  )
}
```

Create: `src/components/upload/FileList.tsx`

```tsx
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { X, FileText } from 'lucide-react'
import type { Artifact } from '@/types/artifact'

interface FileListProps {
  files: Artifact[]
  onRemove?: (id: string) => void
}

export function FileList({ files, onRemove }: FileListProps) {
  if (files.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2">
      {files.map((file) => (
        <Badge
          key={file.artifact_id}
          variant="secondary"
          className="flex items-center gap-1 pr-1"
        >
          <FileText className="h-3 w-3" />
          <span className="max-w-[150px] truncate">{file.file_name}</span>
          {onRemove && (
            <Button
              variant="ghost"
              size="icon"
              className="h-4 w-4 ml-1 hover:bg-destructive/20"
              onClick={() => onRemove(file.artifact_id)}
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </Badge>
      ))}
    </div>
  )
}
```

### 4.4 Main Layout

Create: `src/components/layout/MainLayout.tsx`

```tsx
import { useState, useCallback } from 'react'
import { useSession } from '@/hooks/useSession'
import { ChatContainer } from '@/components/chat/ChatContainer'
import { SessionSidebar } from '@/components/session/SessionSidebar'
import { ArtifactCard } from '@/components/artifacts/ArtifactCard'
import { ArtifactRenderer } from '@/components/artifacts/ArtifactRenderer'
import type { Artifact } from '@/types/artifact'

export function MainLayout() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null)
  const [artifacts, setArtifacts] = useState<Artifact[]>([])

  const { session, createSession } = useSession(currentSessionId || undefined)

  const handleNewSession = useCallback(async () => {
    const newSession = await createSession()
    if (newSession) {
      setCurrentSessionId(newSession.session_id)
      setArtifacts([])
      setSelectedArtifact(null)
    }
  }, [createSession])

  const handleArtifactSelect = useCallback((artifactId: string) => {
    const artifact = artifacts.find(a => a.artifact_id === artifactId)
    if (artifact) {
      setSelectedArtifact(artifact)
    }
  }, [artifacts])

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <SessionSidebar
        currentSessionId={currentSessionId}
        onSessionSelect={setCurrentSessionId}
        onNewSession={handleNewSession}
      />

      {/* Main content */}
      <div className="flex-1 flex">
        {/* Chat area */}
        <div className="flex-1 flex flex-col border-r">
          {currentSessionId ? (
            <ChatContainer
              sessionId={currentSessionId}
              onArtifactSelect={handleArtifactSelect}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              <div className="text-center">
                <h2 className="text-xl font-semibold mb-2">
                  Welcome to AI Data Analyst
                </h2>
                <p className="mb-4">
                  Create a new session to start analyzing your data
                </p>
                <Button onClick={handleNewSession}>
                  New Session
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Artifact panel */}
        <div className="w-[400px] flex flex-col">
          <div className="p-4 border-b">
            <h3 className="font-semibold">Artifacts</h3>
          </div>
          
          {/* Artifact list */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {artifacts.map((artifact) => (
              <ArtifactCard
                key={artifact.artifact_id}
                artifact={artifact}
                isSelected={selectedArtifact?.artifact_id === artifact.artifact_id}
                onClick={() => setSelectedArtifact(artifact)}
              />
            ))}
            {artifacts.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-8">
                Artifacts will appear here as you work
              </p>
            )}
          </div>

          {/* Selected artifact preview */}
          {selectedArtifact && (
            <div className="border-t p-4">
              <ArtifactRenderer artifact={selectedArtifact} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

import { Button } from '@/components/ui/button'
```

---

## State Management

For this application, React's built-in `useState` and custom hooks should be sufficient. However, if the application grows, consider using:

### Option 1: Zustand (Recommended for this project)

```bash
pnpm add zustand
```

Create: `src/stores/sessionStore.ts`

```typescript
import { create } from 'zustand'
import type { Session } from '@/types/session'

interface SessionStore {
  sessions: Session[]
  currentSession: Session | null
  isLoading: boolean
  
  // Actions
  setSessions: (sessions: Session[]) => void
  setCurrentSession: (session: Session | null) => void
  addSession: (session: Session) => void
}

export const useSessionStore = create<SessionStore>((set) => ({
  sessions: [],
  currentSession: null,
  isLoading: false,
  
  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (currentSession) => set({ currentSession }),
  addSession: (session) => set((state) => ({ 
    sessions: [session, ...state.sessions] 
  })),
}))
```

### Option 2: React Context (Simple, Built-in)

Create: `src/context/SessionContext.tsx`

```typescript
import { createContext, useContext, useState, ReactNode } from 'react'
import type { Session } from '@/types/session'

interface SessionContextValue {
  currentSession: Session | null
  setCurrentSession: (session: Session | null) => void
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [currentSession, setCurrentSession] = useState<Session | null>(null)
  
  return (
    <SessionContext.Provider value={{ currentSession, setCurrentSession }}>
      {children}
    </SessionContext.Provider>
  )
}

export function useSessionContext() {
  const context = useContext(SessionContext)
  if (!context) {
    throw new Error('useSessionContext must be used within SessionProvider')
  }
  return context
}
```

---

## Styling Guidelines

### 1. Use Tailwind CSS Classes

```tsx
// Good - using Tailwind
<div className="flex items-center gap-4 p-4 bg-card rounded-lg shadow-sm">

// Avoid - inline styles
<div style={{ display: 'flex', gap: '16px' }}>
```

### 2. Use shadcn/ui Components

```tsx
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

// Use variants for different styles
<Button variant="outline" size="sm">Click Me</Button>
```

### 3. Dark Mode Support

Use `dark:` prefix for dark mode variants:

```tsx
<div className="bg-white dark:bg-slate-900 text-black dark:text-white">
```

### 4. Responsive Design

```tsx
// Mobile-first approach
<div className="flex flex-col md:flex-row lg:grid lg:grid-cols-3">
```

### 5. Add Required Dependencies

```bash
# For markdown rendering
pnpm add react-markdown remark-gfm

# For syntax highlighting
pnpm add prism-react-renderer

# For state management (optional)
pnpm add zustand

# For routing (if needed)
pnpm add react-router-dom
```

---

## Environment Setup

Create: `.env` in frontend root

```env
VITE_API_URL=http://localhost:8011/api/v1
```

Update: `vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5170,
    proxy: {
      '/api': {
        target: 'http://localhost:8011',
        changeOrigin: true,
      },
    },
  },
})
```

---

## Testing Considerations

### Unit Tests

```bash
pnpm add -D vitest @testing-library/react @testing-library/user-event
```

### Component Testing Example

```typescript
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Message } from '@/components/chat/Message'

describe('Message', () => {
  it('renders user message correctly', () => {
    render(
      <Message
        message={{
          message_id: '1',
          session_id: 's1',
          role: 'user',
          content: 'Hello world',
          artifact_ids: [],
          is_error: false,
          created_at: new Date().toISOString(),
          metadata: {},
        }}
      />
    )
    expect(screen.getByText('Hello world')).toBeInTheDocument()
  })
})
```

---

## Summary Checklist

| Phase | Component | Status |
|-------|-----------|--------|
| Setup | Type definitions | ⬜ |
| Setup | API client | ⬜ |
| Setup | Custom hooks | ⬜ |
| Chat | ChatContainer | ⬜ |
| Chat | ChatInput | ⬜ |
| Chat | MessageList | ⬜ |
| Chat | Message | ⬜ |
| Chat | TypingIndicator | ⬜ |
| Artifacts | ArtifactCard | ⬜ |
| Artifacts | ArtifactRenderer | ⬜ |
| Artifacts | ImageArtifact | ⬜ |
| Artifacts | TableArtifact | ⬜ |
| Artifacts | CodeViewer | ⬜ |
| Artifacts | MarkdownArtifact | ⬜ |
| Upload | FileUpload | ⬜ |
| Upload | FileList | ⬜ |
| Layout | MainLayout | ⬜ |
| Session | SessionSidebar | ⬜ |
| State | Session store | ⬜ |
| Config | Environment | ⬜ |

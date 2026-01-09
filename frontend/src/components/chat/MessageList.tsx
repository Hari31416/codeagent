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

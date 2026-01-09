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

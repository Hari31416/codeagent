import { cn } from '@/lib/utils'
import type { Message as MessageType } from '@/types/message'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CodeViewer } from '@/components/artifacts/CodeViewer'
import { User, Bot } from 'lucide-react'
import { TypedDataRenderer } from '@/components/artifacts/TypedDataRenderer'

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
        isUser ? 'items-end' : 'items-start',
        isError && 'border-l-2 border-destructive pl-3'
      )}>
        {/* Iterations (New Standard Format) */}
        {message.iterations && message.iterations.length > 0 ? (
          <div className="flex flex-col gap-4 w-full mt-2">
            {message.iterations.map((iter, i) => (
              <div key={i} className="flex flex-col gap-2 border-l-2 border-muted pl-3">
                <div className="text-xs font-medium text-muted-foreground uppercase">
                  Iteration {iter.iteration}
                </div>

                {/* Thought */}
                {iter.thought && (
                  <Card className="p-3 bg-muted/30 text-sm">
                    <span className="font-semibold text-muted-foreground block mb-1">Thought</span>
                    {iter.thought}
                  </Card>
                )}

                {/* Code */}
                {iter.code && (
                  <div className="mt-1">
                    <span className="text-xs font-semibold text-muted-foreground mb-1 block">Code</span>
                    <CodeViewer code={iter.code} language="python" />
                  </div>
                )}

                {/* Output */}
                {iter.output && (
                  <div className="mt-1">
                    <span className="text-xs font-semibold text-muted-foreground mb-1 block">Output</span>
                    {/* Dynamic typed renderer */}
                    <TypedDataRenderer
                      data={iter.output}
                    />
                  </div>
                )}

                {/* Logs fallback or additional info */}
                {iter.execution_logs && !iter.output && (
                  <div className="mt-1 text-xs font-mono bg-black/5 p-2 rounded whitespace-pre-wrap">
                    {iter.execution_logs}
                  </div>
                )}

                {iter.error && (
                  <div className="text-destructive text-sm bg-destructive/10 p-2 rounded">
                    Error: {iter.error}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          /* Legacy View (for old messages or simple responses) */
          <>
              {/* Thoughts (for assistant messages) */}
              {message.thoughts && !isUser && (
                <Card className="p-3 bg-muted/50 text-sm text-muted-foreground">
                  <p className="font-medium mb-1">Thinking:</p>
                  <p>{message.thoughts}</p>
                </Card>
              )}

              {/* Code block */}
              {message.code && !isUser && (
                <CodeViewer code={message.code} language="python" />
              )}
            </>
        )}

        {/* Primary Content (User Message or Assistant Response) */}
        {message.content && (!message.iterations || message.iterations.length === 0) && (
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
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

import { cn } from '@/lib/utils'
import type { Message as MessageType } from '@/types/message'
import type { StreamEventType } from '@/types/api'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CollapsibleCode } from '@/components/chat/CollapsibleCode'
import { User, Bot, Brain, Code, Play, Check, ChevronRight, ChevronDown } from 'lucide-react'
import { TypedDataRenderer } from '@/components/artifacts/TypedDataRenderer'
import { useState } from 'react'

interface MessageProps {
  message: MessageType
  onArtifactClick?: (artifactId: string) => void
  processingState?: {
    status: StreamEventType | 'idle'
    currentThought: string | null
    iteration: number
    totalIterations: number
  }
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

export function Message({ message, onArtifactClick, processingState }: MessageProps) {
  const isUser = message.role === 'user'
  const isError = message.is_error

  // Use processing state only if this is the assistant message and we have active processing state
  const showTypingIndicator = !isUser && processingState && processingState.status !== 'idle' && processingState.status !== 'error' && processingState.status !== 'completed'
  const config = showTypingIndicator ? (statusConfig[processingState!.status as StreamEventType] || statusConfig.started) : null
  const Icon = config ? config.icon : null

  return (
    <div className={cn(
      'flex gap-3',
      isUser ? 'flex-row-reverse' : 'flex-row'
    )}>
      {/* Avatar */}
      <div className={cn(
        'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
        isUser ? 'bg-primary text-primary-foreground' : 'bg-muted',
        showTypingIndicator && 'animate-pulse'
      )}>
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>



      {/* Content */}
      <div className={cn(
        'flex flex-col gap-1 max-w-[80%]',
        isUser ? 'items-end' : 'items-start'
      )}>

        <div className={cn(
          'flex flex-col gap-2 w-full',
          isUser ? 'items-end' : 'items-start',
          isError && 'border-l-2 border-destructive pl-3'
        )}>
          {/* Iterations (New Standard Format) */}
          {message.iterations && message.iterations.length > 0 ? (
            <div className="flex flex-col gap-4 w-full mt-2">
              {message.iterations.map((iter, i) => {
                const isLastIteration = i === message.iterations!.length - 1
                const hasFinalResult = iter.final_result && isLastIteration

                return (
                  <div key={i} className="flex flex-col gap-2 border-l-2 border-muted pl-3">
                    <div className="text-xs font-medium text-muted-foreground uppercase">
                      Iteration {iter.iteration}
                    </div>

                    {/* Final Result - Shown prominently at the top of the last iteration */}
                    {hasFinalResult && (
                      <Card className="p-4 bg-primary/5 border-primary/20 shadow-sm">
                        <div className="flex items-center gap-2 mb-2 text-primary">
                          <div className="h-2 w-2 rounded-full bg-primary" />
                          <span className="font-semibold text-sm uppercase tracking-wider">Answer</span>
                        </div>
                        <div className="mt-1">
                          <TypedDataRenderer data={iter.final_result!} />
                        </div>
                      </Card>
                    )}

                    {/* Thought (Collapsible) */}
                    {(iter.thought || iter.thoughts) && (
                      <ThoughtAccordion thought={iter.thought || iter.thoughts || ''} />
                    )}

                    {/* Code */}
                    {iter.code && (
                      <CollapsibleCode code={iter.code} language="python" label="Generated Code" />
                    )}

                    {/* Output - Only show if no final_result, or for non-final iterations */}
                    {iter.output && !hasFinalResult && (
                      <div className="mt-1">
                        <span className="text-xs font-semibold text-muted-foreground mb-1 block">Output</span>
                        {/* Dynamic typed renderer */}
                        <TypedDataRenderer
                          data={iter.output}
                        />
                      </div>
                    )}

                    {/* Logs fallback or additional info */}
                    {iter.execution_logs && !iter.output && !hasFinalResult && (
                      <div className="mt-1 text-xs font-mono bg-black/5 p-2 rounded whitespace-pre-wrap">
                        {iter.execution_logs}
                      </div>
                    )}

                    {/* Error */}
                    {iter.error && (
                      <div className="text-destructive text-sm bg-destructive/10 p-2 rounded">
                        Error: {iter.error}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            /* Legacy View (for old messages or simple responses) */
            <>
              {/* Thoughts (for assistant messages) */}
              {message.thoughts && !isUser && (
                  <ThoughtAccordion thought={message.thoughts || ''} />
              )}

              {/* Code block */}
              {message.code && !isUser && (
                <CollapsibleCode code={message.code} language="python" />
              )}
            </>
          )}

          {/* Typing Indicator / Active Status */}
          {showTypingIndicator && config && Icon && (
            <Card className="p-3 bg-muted/20 border-border/50 w-full animate-in fade-in duration-300">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Icon className="h-4 w-4 animate-spin" />
                <span>{config.label}</span>
                {processingState!.iteration > 0 && processingState!.totalIterations > 0 && (
                  <span className="text-xs">
                    (Iteration {processingState!.iteration}/{processingState!.totalIterations})
                  </span>
                )}
              </div>

              {processingState!.currentThought && processingState!.status === 'thinking' && (
                <p className="mt-2 text-sm text-muted-foreground/80 italic border-l-2 border-primary/20 pl-2">
                  {processingState!.currentThought}
                </p>
              )}
            </Card>
          )}

          {/* Primary Content (User Message or Assistant Response) */}
          {message.content && (!message.iterations || message.iterations.length === 0) && (
            <div className={cn(
              "whitespace-pre-wrap break-words",
              isUser && "bg-muted/50 rounded-2xl px-4 py-2.5 rounded-tr-sm"
            )}>
              {message.content}
            </div>
          )}


          {/* Artifact badges */}
          {message.artifact_ids && message.artifact_ids.length > 0 && (
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

          {/* Assistant: Usage Stats + Timestamp */}
          {message.role === 'assistant' && (
            <div className="flex justify-start w-full mt-2 pt-2 border-t border-border/40">
              <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground/60 font-mono items-center">
                {message.usage ? (
                  <>
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500/40" />
                      {message.usage.input_tokens.toLocaleString()} in
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500/40" />
                      {message.usage.output_tokens.toLocaleString()} out
                    </span>
                    {message.usage.estimated_cost_usd > 0 && (
                      <span className="flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-yellow-500/40" />
                        ${message.usage.estimated_cost_usd.toFixed(4)}
                      </span>
                    )}
                    <span className="opacity-50">
                      {message.usage.model}
                    </span>
                    <span className="opacity-50 mx-1">·</span>
                  </>
                ) : null}

                <span className="opacity-70">
                  {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              </div>
            </div>
          )}

          {/* User: Timestamp only */}
          {isUser && (
            <div className="text-[10px] text-muted-foreground/40 px-1 select-none">
              {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </div>
          )}

        </div>
      </div>
    </div>
  )
}

function ThoughtAccordion({ thought }: { thought: string }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <Card className="bg-muted/30 border-border/40 shadow-none overflow-hidden hover:bg-muted/40 transition-colors">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground hover:text-foreground transition-colors text-left"
      >
        {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <span className="font-semibold uppercase tracking-wider">Thought Process</span>
      </button>

      {isOpen && (
        <div className="px-3 pb-3 pt-0 text-sm text-muted-foreground leading-relaxed animate-in slide-in-from-top-1 duration-200">
          <div className="border-t border-border/40 pt-2 mt-1">
            {thought}
          </div>
        </div>
      )}
    </Card>
  )
}

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

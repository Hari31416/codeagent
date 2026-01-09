import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Plus, MessageSquare, Trash2 } from 'lucide-react'
import { getSessions, deleteSession } from '@/api/sessions'
import type { Session } from '@/types/session'
import { cn } from '@/lib/utils'
import { getUserId } from '@/lib/user'

interface SessionSidebarProps {
  currentSessionId: string | null
  onSessionSelect: (sessionId: string | null) => void
  onNewSession: () => void
}

export function SessionSidebar({ currentSessionId, onSessionSelect, onNewSession }: SessionSidebarProps) {
  const [sessions, setSessions] = useState<Session[]>([])

  const loadSessions = async () => {
    try {
      const userId = getUserId()
      const response = await getSessions(userId)
      if (response.success) {
        setSessions(response.data)
      }
    } catch (error) {
      console.error("Failed to load sessions", error)
    }
  }

  useEffect(() => {
    loadSessions()
  }, [currentSessionId])

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation()
    if (confirm('Are you sure you want to delete this session?')) {
      await deleteSession(sessionId)
      loadSessions()
      if (currentSessionId === sessionId) {
        onSessionSelect(null)
      }
    }
  }

  return (
    <div className="w-[260px] border-r flex flex-col h-full bg-muted/30">
      <div className="p-4">
        <Button onClick={onNewSession} className="w-full justify-start gap-2">
          <Plus className="h-4 w-4" />
          New Session
        </Button>
      </div>
      <div className="flex-1 overflow-auto p-2">
        <div className="space-y-1">
          {sessions.map(session => (
            <div
              key={session.session_id}
              onClick={() => onSessionSelect(session.session_id)}
              className={cn(
                "group flex items-center justify-between px-3 py-2 text-sm rounded-md cursor-pointer hover:bg-accent hover:text-accent-foreground",
                currentSessionId === session.session_id ? "bg-accent text-accent-foreground" : "text-muted-foreground"
              )}
            >
              <div className="flex items-center gap-2 truncate">
                <MessageSquare className="h-4 w-4" />
                <span className="truncate">{session.name || 'Untitled Session'}</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-0 group-hover:opacity-100"
                onClick={(e) => handleDelete(e, session.session_id)}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          ))}
          {sessions.length === 0 && (
            <div className="text-center text-sm text-muted-foreground py-4">
              No sessions found
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

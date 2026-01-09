import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Plus, FolderOpen, ChevronDown, ChevronRight, Trash2 } from 'lucide-react'
import { getSessions } from '@/api/sessions'
import type { Session } from '@/types/session'
import type { Project } from '@/types/project'
import { cn } from '@/lib/utils'
import { useEffect } from 'react'
import { getUserId } from '@/lib/user'

interface ProjectSidebarProps {
  projects: Project[]
  selectedProjectId: string | null
  currentSessionId: string | null
  onProjectSelect: (projectId: string) => void
  onSessionSelect: (sessionId: string) => void
  onNewProject: () => void
  onNewSession: (projectId: string) => void
  onDeleteProject: (projectId: string) => void
  lastUpdated?: number
}

export function ProjectSidebar({
  projects,
  selectedProjectId,
  currentSessionId,
  onProjectSelect,
  onSessionSelect,
  onNewProject,
  onNewSession,
  onDeleteProject,
  lastUpdated,
}: ProjectSidebarProps) {
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set())
  const [projectSessions, setProjectSessions] = useState<Record<string, Session[]>>({})

  // Load sessions for a project
  const loadProjectSessions = async (projectId: string) => {
    try {
      const userId = getUserId()
      const response = await getSessions(userId, projectId)
      if (response.success) {
        setProjectSessions(prev => ({
          ...prev,
          [projectId]: response.data,
        }))
      }
    } catch (error) {
      console.error('Failed to load project sessions', error)
    }
  }

  // Expand/collapse project
  const toggleProject = (projectId: string) => {
    setExpandedProjects(prev => {
      const newSet = new Set(prev)
      if (newSet.has(projectId)) {
        newSet.delete(projectId)
      } else {
        newSet.add(projectId)
        // Load sessions when expanding
        loadProjectSessions(projectId)
      }
      return newSet
    })
  }

  // Auto-expand selected project
  useEffect(() => {
    if (selectedProjectId && !expandedProjects.has(selectedProjectId)) {
      setExpandedProjects(prev => new Set([...prev, selectedProjectId]))
      loadProjectSessions(selectedProjectId)
    }
  }, [selectedProjectId])

  // Reload sessions when lastUpdated changes
  useEffect(() => {
    if (selectedProjectId) {
      loadProjectSessions(selectedProjectId)
    }
  }, [lastUpdated, selectedProjectId])

  const handleProjectClick = (projectId: string) => {
    onProjectSelect(projectId)
    if (!expandedProjects.has(projectId)) {
      toggleProject(projectId)
    }
  }

  const handleDeleteProject = (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation()
    if (confirm('Are you sure you want to delete this project? All sessions and files will be deleted.')) {
      onDeleteProject(projectId)
    }
  }

  return (
    <div className="flex flex-col h-full bg-muted/30">
      <div className="p-4 space-y-2">
        <Button onClick={onNewProject} className="w-full justify-start gap-2">
          <Plus className="h-4 w-4" />
          New Project
        </Button>
      </div>

      <div className="flex-1 overflow-auto p-2">
        <div className="space-y-1">
          {projects.map(project => {
            const isExpanded = expandedProjects.has(project.project_id)
            const isSelected = selectedProjectId === project.project_id
            const sessions = projectSessions[project.project_id] || []

            return (
              <div key={project.project_id} className="space-y-0.5">
                {/* Project Header */}
                <div
                  className={cn(
                    'group flex items-center justify-between px-3 py-2 text-sm rounded-md cursor-pointer hover:bg-accent hover:text-accent-foreground',
                    isSelected ? 'bg-accent text-accent-foreground' : 'text-muted-foreground'
                  )}
                  onClick={() => handleProjectClick(project.project_id)}
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        toggleProject(project.project_id)
                      }}
                      className="flex-shrink-0"
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-3 w-3" />
                      ) : (
                        <ChevronRight className="h-3 w-3" />
                      )}
                    </button>
                    <FolderOpen className="h-4 w-4 flex-shrink-0" />
                    <span className="truncate font-medium">{project.name}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 flex-shrink-0"
                    onClick={(e) => handleDeleteProject(e, project.project_id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>

                {/* Sessions List */}
                {isExpanded && (
                  <div className="ml-6 space-y-0.5">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full justify-start gap-2 h-7 text-xs"
                      onClick={(e) => {
                        e.stopPropagation()
                        onNewSession(project.project_id)
                      }}
                    >
                      <Plus className="h-3 w-3" />
                      New Session
                    </Button>
                    {sessions.map(session => (
                      <div
                        key={session.session_id}
                        onClick={() => onSessionSelect(session.session_id)}
                        className={cn(
                          'px-3 py-1.5 text-xs rounded-md cursor-pointer hover:bg-accent hover:text-accent-foreground truncate',
                          currentSessionId === session.session_id
                            ? 'bg-accent/70 text-accent-foreground'
                            : 'text-muted-foreground'
                        )}
                      >
                        {session.name || 'Untitled Session'}
                      </div>
                    ))}
                    {sessions.length === 0 && (
                      <div className="px-3 py-1.5 text-xs text-muted-foreground/50">
                        No sessions yet
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}

          {projects.length === 0 && (
            <div className="text-center text-sm text-muted-foreground py-4">
              No projects found
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

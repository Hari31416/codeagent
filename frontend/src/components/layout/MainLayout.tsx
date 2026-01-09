import { useState, useCallback, useEffect } from 'react'
import { useSession } from '@/hooks/useSession'
import { useProjects } from '@/hooks/useProjects'
import { useArtifacts } from '@/hooks/useArtifacts'
import { ChatContainer } from '@/components/chat/ChatContainer'
import { ProjectSidebar } from '@/components/project/ProjectSidebar'
import { ArtifactsSidebar } from '@/components/artifacts/ArtifactsSidebar'
import type { Artifact } from '@/types/artifact'
import { Button } from '@/components/ui/button'
import { PanelLeft, PanelRight, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function MainLayout() {
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
    const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null)
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const [isArtifactsOpen, setIsArtifactsOpen] = useState(true)
    const [lastUpdated, setLastUpdated] = useState(Date.now())

    // Project creation dialog state
    const [isProjectDialogOpen, setIsProjectDialogOpen] = useState(false)
    const [newProjectName, setNewProjectName] = useState('')
    const [newProjectDescription, setNewProjectDescription] = useState('')

    const { createSession } = useSession(currentSessionId || undefined)
    const {
        projects,
        selectedProjectId,
        selectProject,
        createProject,
        deleteProject,
    } = useProjects()
    const { artifacts, refresh: refreshArtifacts } = useArtifacts(currentSessionId || undefined)

    const handleNewProject = useCallback(() => {
        setIsProjectDialogOpen(true)
    }, [])

    const handleCreateProject = useCallback(async () => {
        if (!newProjectName.trim()) return

        const project = await createProject(newProjectName.trim(), newProjectDescription.trim() || undefined)
        if (project) {
            selectProject(project.project_id)
            setIsProjectDialogOpen(false)
            setNewProjectName('')
            setNewProjectDescription('')
        }
    }, [newProjectName, newProjectDescription, createProject, selectProject])

    const handleNewSession = useCallback(async (projectId: string) => {
        const newSession = await createSession(projectId)
        if (newSession) {
            setCurrentSessionId(newSession.session_id)
            setSelectedArtifact(null)
            setLastUpdated(Date.now())
        }
    }, [createSession])

    const handleProjectSelect = useCallback((projectId: string) => {
        selectProject(projectId)
    }, [selectProject])

    const handleSessionSelect = useCallback((sessionId: string) => {
        setCurrentSessionId(sessionId)
        setSelectedArtifact(null)
    }, [])

    const handleArtifactSelect = useCallback((artifactId: string) => {
        const artifact = artifacts.find(a => a.artifact_id === artifactId)
        if (artifact) {
            setSelectedArtifact(artifact)
            if (!isArtifactsOpen) setIsArtifactsOpen(true)
        }
    }, [artifacts, isArtifactsOpen])

    const handleSidebarArtifactSelect = useCallback((artifactId: string | null) => {
        if (artifactId === null) {
            setSelectedArtifact(null)
        } else {
            handleArtifactSelect(artifactId)
        }
    }, [handleArtifactSelect])

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b') {
                e.preventDefault()
                if (e.shiftKey) {
                    setIsArtifactsOpen(prev => !prev)
                } else {
                    setIsSidebarOpen(prev => !prev)
                }
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [])

    return (
        <div className="flex h-screen bg-background overflow-hidden">
            {/* Project Sidebar */}
            <div className={cn(
                "transition-all duration-300 ease-in-out overflow-hidden bg-muted/30 flex flex-col",
                isSidebarOpen ? "w-[280px] border-r" : "w-0 border-none"
            )}>
                <div className="w-[280px] h-full">
                    <ProjectSidebar
                        projects={projects}
                        selectedProjectId={selectedProjectId}
                        currentSessionId={currentSessionId}
                        onProjectSelect={handleProjectSelect}
                        onSessionSelect={handleSessionSelect}
                        onNewProject={handleNewProject}
                        onNewSession={handleNewSession}
                        onDeleteProject={deleteProject}
                        lastUpdated={lastUpdated}
                    />
                </div>
            </div>

            {/* Main content */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Header / Toggle Bar */}
                <div className="h-12 border-b flex items-center px-4 justify-between bg-background shrink-0">
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                            title={isSidebarOpen ? "Close sidebar" : "Open sidebar"}
                        >
                            <PanelLeft className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={handleNewProject}
                            title="New Project"
                        >
                            <Plus className="h-4 w-4" />
                        </Button>
                        <span className="font-medium text-sm text-muted-foreground ml-2">
                            {currentSessionId ? "Chat Session" : "Select or Create Project"}
                        </span>
                    </div>

                    <div className="flex items-center gap-2">
                        <Button
                            variant={isArtifactsOpen ? "secondary" : "ghost"}
                            size="sm"
                            className="gap-2"
                            onClick={() => setIsArtifactsOpen(!isArtifactsOpen)}
                        >
                            <PanelRight className="h-4 w-4" />
                            <span className="hidden sm:inline">Artifacts</span>
                            {artifacts.length > 0 && (
                                <span className="bg-primary text-primary-foreground text-[10px] px-1.5 py-0.5 rounded-full ml-1">
                                    {artifacts.length}
                                </span>
                            )}
                        </Button>
                    </div>
                </div>

                <div className="flex-1 flex overflow-hidden">
                    {/* Chat area */}
                    <div className="flex-1 flex flex-col min-w-0">
                        {currentSessionId ? (
                            <ChatContainer
                                sessionId={currentSessionId}
                                onArtifactSelect={handleArtifactSelect}
                                onArtifactCreated={refreshArtifacts}
                                onSessionUpdate={() => setLastUpdated(Date.now())}
                            />
                        ) : (
                            <div className="flex-1 flex items-center justify-center text-muted-foreground">
                                <div className="text-center">
                                    <h2 className="text-xl font-semibold mb-2">
                                        Welcome to AI Data Analyst
                                    </h2>
                                    <p className="mb-4">
                                            {projects.length === 0
                                                ? 'Create a project to get started'
                                                : 'Select a project and create a session to start analyzing'}
                                    </p>
                                        <Button onClick={handleNewProject}>
                                            New Project
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Artifact panel */}
                    <ArtifactsSidebar
                        isOpen={isArtifactsOpen}
                        artifacts={artifacts}
                        selectedArtifactId={selectedArtifact?.artifact_id ?? null}
                        onArtifactSelect={handleSidebarArtifactSelect}
                        onToggle={setIsArtifactsOpen}
                    />
                </div>
            </div>

            {/* Project Creation Dialog */}
            <Dialog open={isProjectDialogOpen} onOpenChange={setIsProjectDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Create New Project</DialogTitle>
                        <DialogDescription>
                            Projects help you organize related sessions and files together.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="project-name">Project Name *</Label>
                            <Input
                                id="project-name"
                                placeholder="My Data Analysis Project"
                                value={newProjectName}
                                onChange={(e) => setNewProjectName(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && newProjectName.trim()) {
                                        handleCreateProject()
                                    }
                                }}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="project-description">Description (Optional)</Label>
                            <Input
                                id="project-description"
                                placeholder="Brief description of this project"
                                value={newProjectDescription}
                                onChange={(e) => setNewProjectDescription(e.target.value)}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => {
                                setIsProjectDialogOpen(false)
                                setNewProjectName('')
                                setNewProjectDescription('')
                            }}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={handleCreateProject}
                            disabled={!newProjectName.trim()}
                        >
                            Create Project
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}

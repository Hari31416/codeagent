import { useState, useCallback, useEffect } from 'react'
import { useMediaQuery } from '@/hooks/useMediaQuery'
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
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { MoreVertical, FolderOpen } from 'lucide-react'

import { uploadProjectFile, exportProject } from '@/api/projects'
import { exportSession } from '@/api/sessions'
import { ExportModal } from '@/components/export/ExportModal'
import { Download } from 'lucide-react'

export function MainLayout() {
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
    const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null)
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const [isArtifactsOpen, setIsArtifactsOpen] = useState(true)
    const [lastUpdated, setLastUpdated] = useState(Date.now())
    const [theme, setTheme] = useState<'light' | 'dark'>(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('theme') as 'light' | 'dark'
            if (saved) return saved
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
        }
        return 'light'
    })

    useEffect(() => {
        if (theme === 'dark') {
            document.documentElement.classList.add('dark')
        } else {
            document.documentElement.classList.remove('dark')
        }
        localStorage.setItem('theme', theme)
    }, [theme])

    const toggleTheme = useCallback(() => {
        setTheme(prev => prev === 'light' ? 'dark' : 'light')
    }, [])

    // Export state
    const [isExportModalOpen, setIsExportModalOpen] = useState(false)
    const [exportData, setExportData] = useState<{ metadata: Record<string, any>, markdown: string, filename: string } | null>(null)
    const [isExportLoading, setIsExportLoading] = useState(false)

    const handleExportSession = useCallback(async () => {
        if (!currentSessionId) return
        setIsExportLoading(true)
        setIsExportModalOpen(true)
        try {
            const response = await exportSession(currentSessionId)
            if (response.success && response.data) {
                setExportData(response.data)
            }
        } catch (error) {
            console.error("Failed to export session", error)
        } finally {
            setIsExportLoading(false)
        }
    }, [currentSessionId])

    const handleExportProject = useCallback(async (projectId: string) => {
        setIsExportLoading(true)
        setIsExportModalOpen(true)
        try {
            const response = await exportProject(projectId)
            if (response.success && response.data) {
                setExportData(response.data)
            }
        } catch (error) {
            console.error("Failed to export project", error)
        } finally {
            setIsExportLoading(false)
        }
    }, [])

    // Responsive breakpoints
    const isDesktop = useMediaQuery("(min-width: 1024px)")
    const isMobile = useMediaQuery("(max-width: 768px)")

    const isSidebarCollapsed = !isDesktop

    // Artifacts drawer mode
    const isArtifactsOverlay = !useMediaQuery("(min-width: 1100px)")

    // Handle artifacts panel: close when switching to small screen if it was open
    useEffect(() => {
        if (isArtifactsOverlay && isArtifactsOpen) {
            if (window.innerWidth < 768) setIsArtifactsOpen(false)
        }
    }, [isArtifactsOverlay])


    // Project creation dialog state
    const [isProjectDialogOpen, setIsProjectDialogOpen] = useState(false)
    const [newProjectName, setNewProjectName] = useState('')
    const [newProjectDescription, setNewProjectDescription] = useState('')

    // Get session object to display name
    const { createSession, session } = useSession(currentSessionId || undefined)
    const {
        projects,
        selectedProjectId,
        selectProject,
        createProject,
        deleteProject,
    } = useProjects()
    const { artifacts, refresh: refreshArtifacts } = useArtifacts(currentSessionId || undefined, selectedProjectId || undefined)

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

    const handleSessionSelect = useCallback((sessionId: string | null) => {
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

    const handleUploadProjectFile = useCallback(async (file: File) => {
        if (!selectedProjectId) return
        try {
            await uploadProjectFile(selectedProjectId, file)
            refreshArtifacts()
        } catch (error) {
            console.error("Failed to upload project file", error)
        }
    }, [selectedProjectId, refreshArtifacts])

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Sidebar toggle
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b') {
                e.preventDefault()
                if (e.shiftKey) {
                    setIsArtifactsOpen(prev => !prev)
                } else {
                    setIsSidebarOpen(prev => !prev)
                }
            }

            // New Session
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'j') {
                e.preventDefault()
                if (selectedProjectId) {
                    handleNewSession(selectedProjectId)
                } else if (projects.length > 0) {
                    handleNewSession(projects[0].project_id)
                }
            }

            // Toggle Dark Mode
            if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'l') {
                e.preventDefault()
                toggleTheme()
            }

            // Focus Chat Input
            if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
                e.preventDefault()
                const chatInput = document.querySelector('textarea')
                if (chatInput) chatInput.focus()
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [selectedProjectId, projects, handleNewSession, toggleTheme])

    return (
        <div className="flex h-screen bg-background overflow-hidden">
            {/* Project Sidebar */}
            <div className={cn(
                "transition-all duration-300 ease-in-out overflow-hidden bg-muted/30 flex flex-col",
                isSidebarOpen
                    ? (isSidebarCollapsed ? "w-[60px] border-r" : "w-[280px] border-r")
                    : "w-0 border-none"
            )}>
                <div className={cn("h-full", isSidebarCollapsed ? "w-[60px]" : "w-[280px]")}>
                    <ProjectSidebar
                        projects={projects}
                        selectedProjectId={selectedProjectId}
                        currentSessionId={currentSessionId}
                        onProjectSelect={handleProjectSelect}
                        onSessionSelect={handleSessionSelect}
                        onNewProject={handleNewProject}
                        onNewSession={handleNewSession}
                        onDeleteProject={deleteProject}
                        onExportProject={handleExportProject}
                        lastUpdated={lastUpdated}
                        collapsed={isSidebarCollapsed}
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
                            onClick={() => {
                                if (selectedProjectId) {
                                    handleNewSession(selectedProjectId)
                                } else if (projects.length > 0) {
                                    handleNewSession(projects[0].project_id)
                                } else {
                                    handleNewProject()
                                }
                            }}
                            title={selectedProjectId || projects.length > 0 ? "New Session" : "New Project"}
                        >
                            <Plus className="h-4 w-4" />
                        </Button>
                        <div className="flex flex-col">
                            <div className="flex items-center text-sm font-medium text-foreground">
                                {currentSessionId ? (
                                    isMobile ? (
                                        // Mobile: Show only session name
                                        <span className="truncate max-w-[150px]">
                                            {session?.name || 'Chat Session'}
                                        </span>
                                    ) : (
                                        // Desktop: Project > Session
                                        <div className="flex items-center gap-2 text-muted-foreground">
                                            <span className="truncate max-w-[150px]">
                                                {projects.find(p => p.project_id === selectedProjectId)?.name || 'Project'}
                                            </span>
                                            <span>/</span>
                                            <span className="text-foreground truncate max-w-[200px]">
                                                {session?.name || 'Chat Session'}
                                            </span>
                                        </div>
                                    )
                                ) : (
                                    <span className="text-muted-foreground">Select or Create Project</span>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        {/* Unified Actions Menu for Mobile */}
                        {isMobile ? (
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" size="icon">
                                        <MoreVertical className="h-4 w-4" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                    <DropdownMenuItem onClick={() => {
                                        if (selectedProjectId) {
                                            handleNewSession(selectedProjectId)
                                        } else if (projects.length > 0) {
                                            handleNewSession(projects[0].project_id)
                                        } else {
                                            handleNewProject()
                                        }
                                    }}>
                                        <Plus className="mr-2 h-4 w-4" />
                                        <span>New Session</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={handleNewProject}>
                                        <FolderOpen className="mr-2 h-4 w-4" />
                                        <span>New Project</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => setIsArtifactsOpen(!isArtifactsOpen)}>
                                        <PanelRight className="mr-2 h-4 w-4" />
                                        <span>{isArtifactsOpen ? "Hide" : "Show"} Artifacts</span>
                                    </DropdownMenuItem>
                                    {currentSessionId && (
                                        <DropdownMenuItem onClick={handleExportSession}>
                                            <Download className="mr-2 h-4 w-4" />
                                            <span>Export Session</span>
                                        </DropdownMenuItem>
                                    )}
                                    {selectedProjectId && (
                                        <DropdownMenuItem onClick={() => handleExportProject(selectedProjectId)}>
                                            <Download className="mr-2 h-4 w-4" />
                                            <span>Export Project</span>
                                        </DropdownMenuItem>
                                    )}
                                </DropdownMenuContent>
                            </DropdownMenu>
                        ) : (
                            // Desktop Actions
                            <>
                                    {currentSessionId && (
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={handleExportSession}
                                            title="Export Session"
                                        >
                                            <Download className="h-4 w-4" />
                                        </Button>
                                    )}
                                <Button
                                    variant="ghost"
                                    size="icon"
                                        onClick={toggleTheme}
                                        title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
                                >
                                        {theme === 'light' ? (
                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-moon"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" /></svg>
                                        ) : (
                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-sun"><circle cx="12" cy="12" r="4" /><path d="M12 2v2" /><path d="M12 20v2" /><path d="m4.93 4.93 1.41 1.41" /><path d="m17.66 17.66 1.41 1.41" /><path d="M2 12h2" /><path d="M22 12h2" /><path d="m4.93 19.07 1.41-1.41" /><path d="m17.66 6.34 1.41-1.41" /></svg>
                                        )}
                                </Button>
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
                            </>
                        )}
                    </div>
                </div>

                <div className="flex-1 flex overflow-hidden">
                    {/* Chat area */}
                    <div className="flex-1 flex flex-col min-w-0">
                        {currentSessionId ? (
                            <div className="mx-auto w-full max-w-[900px] h-full">
                                <ChatContainer
                                    sessionId={currentSessionId}
                                    onArtifactSelect={handleArtifactSelect}
                                    onArtifactCreated={refreshArtifacts}
                                    onSessionUpdate={() => setLastUpdated(Date.now())}
                                />
                            </div>
                        ) : (
                            <div className="flex-1 flex items-center justify-center text-muted-foreground">
                                <div className="text-center">
                                    <h2 className="text-xl font-semibold mb-2">
                                        Welcome to AI Data Analyst
                                    </h2>
                                    <p className="mb-4">
                                            {selectedProjectId
                                                ? 'Create a new session to start analyzing'
                                                : projects.length === 0
                                                    ? 'Create a project to get started'
                                                    : 'Select a project to view sessions or create a new one'}
                                    </p>
                                        {selectedProjectId ? (
                                            <Button onClick={() => handleNewSession(selectedProjectId)}>
                                                New Session
                                            </Button>
                                        ) : (
                                        <Button onClick={handleNewProject}>
                                            New Project
                                                </Button>
                                        )}
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
                        projectId={selectedProjectId || undefined}
                        onUploadProjectFile={handleUploadProjectFile}
                        isOverlay={isArtifactsOverlay}
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
            <ExportModal
                open={isExportModalOpen}
                onOpenChange={setIsExportModalOpen}
                exportData={exportData}
                isLoading={isExportLoading}
            />
        </div>
    )
}

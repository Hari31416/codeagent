import { useState, useCallback } from 'react'
import { useSession } from '@/hooks/useSession'
import { useArtifacts } from '@/hooks/useArtifacts'
import { ChatContainer } from '@/components/chat/ChatContainer'
import { SessionSidebar } from '@/components/session/SessionSidebar'
import { ArtifactCard } from '@/components/artifacts/ArtifactCard'
import { ArtifactRenderer } from '@/components/artifacts/ArtifactRenderer'
import type { Artifact } from '@/types/artifact'
import { Button } from '@/components/ui/button'
import { PanelLeft, PanelRight, X, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'

export function MainLayout() {
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
    const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null)
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const [isArtifactsOpen, setIsArtifactsOpen] = useState(true)

    const { createSession } = useSession(currentSessionId || undefined)
    const { artifacts, refresh: refreshArtifacts } = useArtifacts(currentSessionId || undefined)

    const handleNewSession = useCallback(async () => {
        const newSession = await createSession()
        if (newSession) {
            setCurrentSessionId(newSession.session_id)
            setSelectedArtifact(null)
            if (!isSidebarOpen) setIsSidebarOpen(true)
        }
    }, [createSession, isSidebarOpen])

    const handleArtifactSelect = useCallback((artifactId: string) => {
        const artifact = artifacts.find(a => a.artifact_id === artifactId)

        if (artifact) {
            setSelectedArtifact(artifact)
            if (!isArtifactsOpen) setIsArtifactsOpen(true)
        }
    }, [artifacts, isArtifactsOpen])

    return (
        <div className="flex h-screen bg-background overflow-hidden">
            {/* Sidebar */}
            <div className={cn(
                "transition-all duration-300 ease-in-out overflow-hidden border-r bg-muted/30 flex flex-col",
                isSidebarOpen ? "w-[260px]" : "w-[60px]"
            )}>
                {isSidebarOpen ? (
                    <div className="w-[260px] h-full">
                        <SessionSidebar
                            currentSessionId={currentSessionId}
                            onSessionSelect={setCurrentSessionId}
                            onNewSession={handleNewSession}
                        />
                    </div>
                ) : (
                    <div className="flex flex-col items-center h-full">
                        <div className="h-12 w-full flex items-center justify-center border-b shrink-0">
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={handleNewSession}
                                title="New Session"
                                className="h-9 w-9"
                            >
                                <Plus className="h-5 w-5" />
                            </Button>
                        </div>
                    </div>
                )}
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
                        <span className="font-medium text-sm text-muted-foreground">
                            {currentSessionId ? "Chat Session" : "New Chat"}
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
                    <div className={cn(
                        "transition-all duration-300 ease-in-out overflow-hidden border-l bg-background",
                        isArtifactsOpen ? "w-[400px]" : "w-0 border-none"
                    )}>
                        <div className="w-[400px] flex flex-col h-full">
                            <div className="p-4 border-b flex items-center justify-between">
                                <h3 className="font-semibold">Artifacts</h3>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8"
                                    onClick={() => setIsArtifactsOpen(false)}
                                >
                                    <X className="h-4 w-4" />
                                </Button>
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
                                <div className="border-t p-2 h-1/2 min-h-[400px] flex flex-col">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs font-medium truncate max-w-[200px]">
                                            {selectedArtifact.file_name}
                                        </span>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6"
                                            onClick={() => setSelectedArtifact(null)}
                                        >
                                            <X className="h-3 w-3" />
                                        </Button>
                                    </div>
                                    <div className="flex-1 overflow-hidden rounded-md border bg-muted/50">
                                        <ArtifactRenderer artifact={selectedArtifact} />
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

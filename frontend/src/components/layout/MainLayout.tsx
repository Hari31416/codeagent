import { useState, useCallback } from 'react'
import { useSession } from '@/hooks/useSession'
import { useArtifacts } from '@/hooks/useArtifacts'
import { ChatContainer } from '@/components/chat/ChatContainer'
import { SessionSidebar } from '@/components/session/SessionSidebar'
import { ArtifactCard } from '@/components/artifacts/ArtifactCard'
import { ArtifactRenderer } from '@/components/artifacts/ArtifactRenderer'
import type { Artifact } from '@/types/artifact'
import { Button } from '@/components/ui/button'

export function MainLayout() {
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
    const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null)

    const { createSession } = useSession(currentSessionId || undefined)
    const { artifacts, refresh: refreshArtifacts } = useArtifacts(currentSessionId || undefined)

    const handleNewSession = useCallback(async () => {
        const newSession = await createSession()
        if (newSession) {
            setCurrentSessionId(newSession.session_id)
            setSelectedArtifact(null)
        }
    }, [createSession])

    const handleArtifactSelect = useCallback((artifactId: string) => {
        const artifact = artifacts.find(a => a.artifact_id === artifactId)

        if (artifact) {
            setSelectedArtifact(artifact)
        }
    }, [artifacts])

    return (
        <div className="flex h-screen bg-background">
            {/* Sidebar */}
            <SessionSidebar
                currentSessionId={currentSessionId}
                onSessionSelect={setCurrentSessionId}
                onNewSession={handleNewSession}
            />

            {/* Main content */}
            <div className="flex-1 flex">
                {/* Chat area */}
                <div className="flex-1 flex flex-col border-r">
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
                <div className="w-[400px] flex flex-col">
                    <div className="p-4 border-b">
                        <h3 className="font-semibold">Artifacts</h3>
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
                        <div className="border-t p-4">
                            <ArtifactRenderer artifact={selectedArtifact} />
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

import { useState, useEffect, useCallback, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { ArtifactCard } from './ArtifactCard'
import { ArtifactRenderer } from './ArtifactRenderer'
import type { Artifact } from '@/types/artifact'
import { X, ArrowLeft, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ArtifactsSidebarProps {
    isOpen: boolean
    artifacts: Artifact[]
    selectedArtifactId: string | null
    onArtifactSelect: (artifactId: string | null) => void
    onToggle: (isOpen: boolean) => void
}

export function ArtifactsSidebar({
    isOpen,
    artifacts,
    selectedArtifactId,
    onArtifactSelect,
    onToggle
}: ArtifactsSidebarProps) {
    const [width, setWidth] = useState(400)
    const [isResizing, setIsResizing] = useState(false)
    const sidebarRef = useRef<HTMLDivElement>(null)

    const startResizing = useCallback((e: React.MouseEvent) => {
        e.preventDefault()
        setIsResizing(true)
    }, [])

    const stopResizing = useCallback(() => {
        setIsResizing(false)
    }, [])

    const resize = useCallback((mouseMoveEvent: MouseEvent) => {
        if (isResizing) {
            const newWidth = document.body.clientWidth - mouseMoveEvent.clientX
            // Min width 300px, Max width 800px or 50% of screen
            if (newWidth > 300 && newWidth < Math.min(800, document.body.clientWidth * 0.8)) {
                setWidth(newWidth)
            }
        }
    }, [isResizing])

    useEffect(() => {
        if (isResizing) {
            window.addEventListener("mousemove", resize)
            window.addEventListener("mouseup", stopResizing)
        }

        return () => {
            window.removeEventListener("mousemove", resize)
            window.removeEventListener("mouseup", stopResizing)
        }
    }, [isResizing, resize, stopResizing])

    const selectedArtifact = artifacts.find(a => a.artifact_id === selectedArtifactId)

    return (
        <div
            ref={sidebarRef}
            className={cn(
                "border-l bg-background flex flex-col h-full relative shrink-0",
                !isResizing && "transition-[width] duration-300 ease-in-out",
                isOpen ? "" : "border-none"
            )}
            style={{ width: isOpen ? width : 0 }}
        >
            {/* Resize Handle */}
            <div
                className={cn(
                    "absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize hover:bg-primary/20 z-50 transition-colors",
                    isResizing && "bg-primary/20 w-[100vw] -left-[50vw]" // Expand hit area while dragging
                )}
                // Use a nested div for the visual handle so the hit area logic doesn't mess up layout if we want a thin line
                // Actually, let's keep it simple: A thin strip on the left edge.
                style={{ width: '4px', transform: 'translateX(-2px)' }}
                onMouseDown={startResizing}
            />

            {/* Container for content */}
            <div
                className="flex flex-col h-full overflow-hidden"
                style={{ width: width }}
            >

                {/* Header */}
                <div className="h-14 border-b flex items-center justify-between px-4 shrink-0 bg-muted/10">
                    {selectedArtifact ? (
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 shrink-0"
                                onClick={() => onArtifactSelect(null)}
                                title="Back to list"
                            >
                                <ArrowLeft className="h-4 w-4" />
                            </Button>
                            <h3 className="font-semibold truncate text-sm" title={selectedArtifact.file_name}>
                                {selectedArtifact.file_name}
                            </h3>
                        </div>
                    ) : (
                        <h3 className="font-semibold">Artifacts</h3>
                    )}

                    <div className="flex items-center gap-1 pl-2">
                        {selectedArtifact?.presigned_url && (
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => window.open(selectedArtifact.presigned_url, '_blank')}
                                title="Open in new tab"
                            >
                                <ExternalLink className="h-4 w-4" />
                            </Button>
                        )}
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => onToggle(false)}
                            title="Close panel"
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                </div>

                {/* Content Area */}
                <div className="flex-1 overflow-hidden relative">

                    {selectedArtifact ? (
                        // DETAIL VIEW
                        <div className="absolute inset-0 flex flex-col bg-background animate-in slide-in-from-right-4 duration-200">
                            <div className="flex-1 overflow-auto p-4">
                                <ArtifactRenderer artifact={selectedArtifact} />
                            </div>
                        </div>
                    ) : (
                        // LIST VIEW
                        <div className="absolute inset-0 overflow-y-auto p-4 space-y-3 animate-in fade-in duration-200">
                            {artifacts.length === 0 && (
                                <div className="flex flex-col items-center justify-center h-40 text-center text-muted-foreground p-4">
                                    <p className="text-sm">No artifacts yet.</p>
                                    <p className="text-xs mt-1">Files created during the session will appear here.</p>
                                </div>
                            )}

                            {artifacts.map((artifact) => (
                                <ArtifactCard
                                    key={artifact.artifact_id}
                                    artifact={artifact}
                                    isSelected={false} // Selection is now "view mode" so card isn't selected in list
                                    onClick={() => onArtifactSelect(artifact.artifact_id)}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { ArtifactCard } from './ArtifactCard'
import { ArtifactRenderer } from './ArtifactRenderer'
import type { Artifact } from '@/types/artifact'
import { X, ArrowLeft, ExternalLink, Upload, FileText, Layers } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ArtifactsSidebarProps {
    isOpen: boolean
    artifacts: Artifact[]
    selectedArtifactId: string | null
    onArtifactSelect: (artifactId: string | null) => void
    onToggle: (isOpen: boolean) => void
    projectId?: string
    onUploadProjectFile?: (file: File) => Promise<void>
}

export function ArtifactsSidebar({
    isOpen,
    artifacts,
    selectedArtifactId,
    onArtifactSelect,
    onToggle,
    projectId,
    onUploadProjectFile
}: ArtifactsSidebarProps) {
    const [width, setWidth] = useState(400)
    const [isResizing, setIsResizing] = useState(false)
    const [isUploading, setIsUploading] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)
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

    // Split artifacts into Project and Session
    const { projectArtifacts, sessionArtifacts } = useMemo(() => {
        const project: Artifact[] = []
        const session: Artifact[] = []

        artifacts.forEach(artifact => {
            // If it has a project_id and NO session_id, it is a project file
            // OR if it explicitly says keys project_id and session_id logic
            if (artifact.project_id && !artifact.session_id) {
                project.push(artifact)
            } else {
                session.push(artifact)
            }
        })
        return { projectArtifacts: project, sessionArtifacts: session }
    }, [artifacts])

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0 && onUploadProjectFile) {
            const file = e.target.files[0]
            try {
                setIsUploading(true)
                await onUploadProjectFile(file)
                // Clear input
                if (fileInputRef.current) {
                    fileInputRef.current.value = ''
                }
            } catch (error) {
                console.error("Upload failed", error)
            } finally {
                setIsUploading(false)
            }
        }
    }

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
                            <div className="absolute inset-0 overflow-y-auto p-4 space-y-6 animate-in fade-in duration-200">

                                {/* Project Files Section */}
                                {(projectArtifacts.length > 0 || onUploadProjectFile) && (
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                                                <Layers className="h-4 w-4" />
                                                <span>Project Files ({projectArtifacts.length})</span>
                                            </div>
                                            {onUploadProjectFile && (
                                                <div>
                                                    <input
                                                        type="file"
                                                        ref={fileInputRef}
                                                        className="hidden"
                                                        onChange={handleFileChange}
                                                    />
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        className="h-7 text-xs gap-1"
                                                        onClick={() => fileInputRef.current?.click()}
                                                        disabled={isUploading}
                                                    >
                                                        <Upload className="h-3 w-3" />
                                                        {isUploading ? 'Uploading...' : 'Upload'}
                                                    </Button>
                                                </div>
                                            )}
                                        </div>

                                        <div className="space-y-2">
                                            {projectArtifacts.length === 0 ? (
                                                <div className="text-center p-3 border border-dashed rounded-md text-muted-foreground text-xs">
                                                    No project files uploaded.
                                                </div>
                                            ) : (
                                                projectArtifacts.map((artifact) => (
                                                    <ArtifactCard
                                                        key={artifact.artifact_id}
                                                        artifact={artifact}
                                                        isSelected={false}
                                                        onClick={() => onArtifactSelect(artifact.artifact_id)}
                                                    // Optional: add visual distinction for project files
                                                    />
                                                ))
                                            )}
                                        </div>
                                </div>
                            )}

                                {/* Session Files Section */}
                                <div className="space-y-3">
                                    <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                                        <FileText className="h-4 w-4" />
                                        <span>Session Files ({sessionArtifacts.length})</span>
                                    </div>

                                    <div className="space-y-2">
                                        {sessionArtifacts.length === 0 ? (
                                            <div className="flex flex-col items-center justify-center h-20 text-center text-muted-foreground p-4 border border-dashed rounded-md">
                                                <p className="text-xs">No session outputs yet.</p>
                                            </div>
                                        ) : (
                                            sessionArtifacts.map((artifact) => (
                                                <ArtifactCard
                                                    key={artifact.artifact_id}
                                                    artifact={artifact}
                                                    isSelected={false}
                                                    onClick={() => onArtifactSelect(artifact.artifact_id)}
                                                />
                                            ))
                                        )}
                                    </div>
                                </div>

                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

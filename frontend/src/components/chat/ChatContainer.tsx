import { useCallback, useState } from 'react'
import { useChat } from '@/hooks/useChat'
import { useFileUpload } from '@/hooks/useFileUpload'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { FileUpload } from '@/components/upload/FileUpload'
import { FileList } from '@/components/upload/FileList'

interface ChatContainerProps {
    sessionId: string
    onArtifactSelect?: (artifactId: string) => void
    onArtifactCreated?: () => void
    onSessionUpdate?: () => void
}

export function ChatContainer({ sessionId, onArtifactSelect, onArtifactCreated, onSessionUpdate }: ChatContainerProps) {
    const [attachedFileIds, setAttachedFileIds] = useState<string[]>([])
    const [selectedModel, setSelectedModel] = useState<string>('')

    const {
        messages,
        state,
        sendMessage,
        isProcessing,
        isAwaitingClarification,
        pendingClarification,
    } = useChat({
        sessionId,
        onSessionRenamed: onSessionUpdate,
        onArtifactsCreated: (ids) => {
            if (onArtifactCreated) {
                onArtifactCreated()
            }

            // Optionally auto-select first artifact
            if (ids.length > 0 && onArtifactSelect) {
                onArtifactSelect(ids[0])
            }
        }
    })

    const {
        isUploading,
        progress,
        uploadedFiles,
        upload,
        clearUploads
    } = useFileUpload(sessionId)

    const handleSend = useCallback(async (content: string) => {
        await sendMessage(content, attachedFileIds, selectedModel || undefined)
        setAttachedFileIds([])
        clearUploads()
    }, [sendMessage, attachedFileIds, clearUploads, selectedModel])

    const handleFilesSelected = useCallback(async (files: File[]) => {
        const artifacts = await upload(files)
        if (onArtifactCreated) {
            onArtifactCreated()
        }
        setAttachedFileIds(prev => [...prev, ...artifacts.map(a => a.artifact_id)])
    }, [upload, onArtifactCreated])

    return (
        <div className="flex flex-col h-full">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4">
                <MessageList
                    messages={messages}
                    onArtifactClick={onArtifactSelect}
                    processingState={isProcessing ? state : undefined}
                />
            </div>

            {/* Attached files preview */}
            {uploadedFiles.length > 0 && (
                <div className="px-4 py-2 border-t">
                    <FileList
                        files={uploadedFiles}
                        onRemove={(id) => {
                            setAttachedFileIds(prev => prev.filter(fid => fid !== id))
                        }}
                    />
                </div>
            )}

            {/* Input area */}
            <div className="p-4 border-t flex flex-col items-center gap-2">
                {isAwaitingClarification && pendingClarification && (
                    <div className="w-full max-w-3xl px-4 py-2 bg-primary/5 border border-primary/20 rounded-lg text-sm text-primary animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <span className="font-semibold mr-2">Clarification needed:</span>
                        {pendingClarification}
                    </div>
                )}
                <div className="w-full max-w-3xl">
                    <ChatInput
                        onSend={handleSend}
                        disabled={isProcessing || isUploading}
                        isClarifying={isAwaitingClarification}
                        placeholder={
                            isProcessing ? 'Processing...' :
                                isAwaitingClarification ? 'Provide clarification...' :
                                    'Ask about your data...'
                        }
                        selectedModel={selectedModel}
                        onModelChange={setSelectedModel}
                        actions={
                            <FileUpload
                                onFilesSelected={handleFilesSelected}
                                isUploading={isUploading}
                                progress={progress}
                            />
                        }
                    />
                </div>
            </div>
        </div>
    )
}

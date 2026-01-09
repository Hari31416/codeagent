import { useCallback, useState } from 'react'
import { useChat } from '@/hooks/useChat'
import { useFileUpload } from '@/hooks/useFileUpload'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { TypingIndicator } from './TypingIndicator'
import { FileUpload } from '@/components/upload/FileUpload'
import { FileList } from '@/components/upload/FileList'

interface ChatContainerProps {
    sessionId: string
    onArtifactSelect?: (artifactId: string) => void
    onArtifactCreated?: () => void
}

export function ChatContainer({ sessionId, onArtifactSelect, onArtifactCreated }: ChatContainerProps) {
    const [attachedFileIds, setAttachedFileIds] = useState<string[]>([])

    const {
        messages,
        state,
        sendMessage,
        isProcessing,
    } = useChat({
        sessionId,
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
        await sendMessage(content, attachedFileIds)
        setAttachedFileIds([])
        clearUploads()
    }, [sendMessage, attachedFileIds, clearUploads])

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
                />

                {isProcessing && (
                    <TypingIndicator
                        status={state.status}
                        thought={state.currentThought}
                        iteration={state.iteration}
                        totalIterations={state.totalIterations}
                    />
                )}
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
            <div className="p-4 border-t">
                <div className="flex gap-2">
                    <FileUpload
                        onFilesSelected={handleFilesSelected}
                        isUploading={isUploading}
                        progress={progress}
                    />
                    <ChatInput
                        onSend={handleSend}
                        disabled={isProcessing || isUploading}
                        placeholder={isProcessing ? 'Processing...' : 'Ask about your data...'}
                    />
                </div>
            </div>
        </div>
    )
}

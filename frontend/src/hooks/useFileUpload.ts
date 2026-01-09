import { useState, useCallback } from 'react'
import { uploadFile } from '@/api/upload'
import type { Artifact } from '@/types/artifact'

interface UploadState {
  isUploading: boolean
  progress: number
  error: Error | null
}

export function useFileUpload(sessionId: string) {
  const [state, setState] = useState<UploadState>({
    isUploading: false,
    progress: 0,
    error: null,
  })
  const [uploadedFiles, setUploadedFiles] = useState<Artifact[]>([])

  const upload = useCallback(async (files: File[]): Promise<Artifact[]> => {
    setState({ isUploading: true, progress: 0, error: null })
    
    const artifacts: Artifact[] = []
    
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        
        const response = await uploadFile(
          sessionId,
          file,
          (progress) => {
            // Calculate overall progress across all files
            const overallProgress = ((i / files.length) + (progress / 100 / files.length)) * 100
            setState(prev => ({ ...prev, progress: Math.round(overallProgress) }))
          }
        )
        
        if (response.success && response.data) {
          const artifact: Artifact = {
            artifact_id: response.data.artifact_id,
            session_id: sessionId,
            file_name: response.data.file_name,
            file_type: response.data.file_type as Artifact['file_type'],
            mime_type: 'application/octet-stream',
            size_bytes: response.data.size_bytes,
            presigned_url: response.data.presigned_url,
            created_at: new Date().toISOString(),
            metadata: {},
          }
          artifacts.push(artifact)
        }
      }
      
      setUploadedFiles(prev => [...prev, ...artifacts])
      setState({ isUploading: false, progress: 100, error: null })
      
      return artifacts
      
    } catch (e) {
      setState({ isUploading: false, progress: 0, error: e as Error })
      throw e
    }
  }, [sessionId])

  const clearUploads = useCallback(() => {
    setUploadedFiles([])
  }, [])

  return {
    ...state,
    uploadedFiles,
    upload,
    clearUploads,
  }
}

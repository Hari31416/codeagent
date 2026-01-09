import { useState, useEffect } from 'react'
import type { Artifact } from '@/types/artifact'
import { ImageArtifact } from './ImageArtifact'
import { TableArtifact } from './TableArtifact'
import { CodeViewer } from './CodeViewer'
import { MarkdownArtifact } from './MarkdownArtifact'
import { Card } from '@/components/ui/card'
import { Loader2 } from 'lucide-react'

interface ArtifactRendererProps {
  artifact: Artifact
}

export function ArtifactRenderer({ artifact }: ArtifactRendererProps) {
  const [content, setContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!artifact.presigned_url) {
      setError(new Error('No URL available'))
      setLoading(false)
      return
    }

    // For images, we don't need to fetch content
    if (['png', 'jpg', 'jpeg', 'gif'].includes(artifact.file_type)) {
      setLoading(false)
      return
    }

    // Fetch text content for other types
    fetch(artifact.presigned_url)
      .then(res => res.text())
      .then(text => {
        setContent(text)
        setLoading(false)
      })
      .catch(err => {
        setError(err)
        setLoading(false)
      })
  }, [artifact])

  if (loading) {
    return (
      <Card className="p-8 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-4 text-destructive">
        Failed to load artifact: {error.message}
      </Card>
    )
  }

  // Render based on file type
  switch (artifact.file_type) {
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif':
      return <ImageArtifact src={artifact.presigned_url!} alt={artifact.file_name} />
    
    case 'csv':
    case 'xlsx':
    case 'xls':
      return <TableArtifact content={content!} fileType={artifact.file_type} />
    
    case 'py':
      return <CodeViewer code={content!} language="python" />
    
    case 'json':
      return <CodeViewer code={content!} language="json" />
    
    case 'md':
      return <MarkdownArtifact content={content!} />
    
    case 'html':
      return (
        <Card className="p-4">
          <iframe 
            srcDoc={content!} 
            className="w-full h-[600px] border-0"
            sandbox="allow-scripts"
          />
        </Card>
      )
    
    default:
      return (
        <Card className="p-4">
          <pre className="whitespace-pre-wrap text-sm">{content}</pre>
        </Card>
      )
  }
}

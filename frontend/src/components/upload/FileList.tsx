import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { X, FileText } from 'lucide-react'
import type { Artifact } from '@/types/artifact'

interface FileListProps {
  files: Artifact[]
  onRemove?: (id: string) => void
}

export function FileList({ files, onRemove }: FileListProps) {
  if (files.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2">
      {files.map((file) => (
        <Badge
          key={file.artifact_id}
          variant="secondary"
          className="flex items-center gap-1 pr-1"
        >
          <FileText className="h-3 w-3" />
          <span className="max-w-[150px] truncate">{file.file_name}</span>
          {onRemove && (
            <Button
              variant="ghost"
              size="icon"
              className="h-4 w-4 ml-1 hover:bg-destructive/20"
              onClick={() => onRemove(file.artifact_id)}
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </Badge>
      ))}
    </div>
  )
}

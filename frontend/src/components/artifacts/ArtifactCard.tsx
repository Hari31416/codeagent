import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { Artifact } from '@/types/artifact'
import { FileImage, FileSpreadsheet, FileCode, FileText, File } from 'lucide-react'

interface ArtifactCardProps {
  artifact: Artifact
  onClick?: () => void
  isSelected?: boolean
}

const typeIcons: Record<string, React.ElementType> = {
  png: FileImage,
  jpg: FileImage,
  jpeg: FileImage,
  gif: FileImage,
  csv: FileSpreadsheet,
  xlsx: FileSpreadsheet,
  xls: FileSpreadsheet,
  py: FileCode,
  json: FileCode,
  md: FileText,
  txt: FileText,
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

export function ArtifactCard({ artifact, onClick, isSelected }: ArtifactCardProps) {
  const Icon = typeIcons[artifact.file_type] || File

  return (
    <Card
      className={`p-3 cursor-pointer transition-all hover:shadow-md ${
        isSelected ? 'ring-2 ring-primary' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-md bg-muted">
          <Icon className="h-5 w-5 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{artifact.file_name}</p>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="secondary" className="text-xs">
              {artifact.file_type.toUpperCase()}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {formatBytes(artifact.size_bytes)}
            </span>
          </div>
        </div>
      </div>
    </Card>
  )
}

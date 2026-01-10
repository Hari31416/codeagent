import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { Artifact } from '@/types/artifact'
import { FileImage, FileSpreadsheet, FileCode, FileText, File, Download, Maximize2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ArtifactCardProps {
  artifact: Artifact
  onClick?: () => void
  onDownload?: (e: React.MouseEvent) => void
  onExpand?: (e: React.MouseEvent) => void
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

function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: 'numeric' }).format(date)
  } catch {
    return ''
  }
}

export function ArtifactCard({ artifact, onClick, onDownload, onExpand, isSelected }: ArtifactCardProps) {
  const Icon = typeIcons[artifact.file_type] || File
  const isImage = ['png', 'jpg', 'jpeg', 'gif'].includes(artifact.file_type)

  return (
    <Card
      className={cn(
        "group relative cursor-pointer transition-all hover:shadow-md overflow-hidden border-border/50",
        isSelected ? 'ring-2 ring-primary border-primary' : '',
        isImage ? 'p-0' : 'p-3'
      )}
      onClick={onClick}
    >
      {isImage && artifact.presigned_url ? (
        // Gallery/Thumbnail View for Images
        <div className="relative aspect-video w-full bg-muted/50 overflow-hidden">
          <img
            src={artifact.presigned_url}
            alt={artifact.file_name}
            className="w-full h-full object-cover transition-transform group-hover:scale-105"
            loading="lazy"
          />
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-3 pt-8 opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-between">
            <div className="min-w-0 flex-1 mr-2">
              <p className="text-white text-xs font-medium truncate">{artifact.file_name}</p>
              <p className="text-white/70 text-[10px]">{formatBytes(artifact.size_bytes)}</p>
            </div>
            <div className="flex gap-1 shrink-0">
              {onDownload && (
                <Button variant="ghost" size="icon" className="h-6 w-6 text-white hover:text-white hover:bg-white/20" onClick={onDownload}>
                  <Download className="h-3 w-3" />
                </Button>
              )}
              {onExpand && (
                <Button variant="ghost" size="icon" className="h-6 w-6 text-white hover:text-white hover:bg-white/20" onClick={onExpand}>
                  <Maximize2 className="h-3 w-3" />
                </Button>
              )}
            </div>
          </div>
        </div>
      ) : (
      // List View for other files
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-lg bg-muted/50 group-hover:bg-muted transition-colors">
              <Icon className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium text-sm truncate group-hover:text-primary transition-colors">
                  {artifact.file_name}
                </p>
                <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                  {onDownload && (
                    <Button variant="ghost" size="icon" className="h-6 w-6" onClick={(e) => { e.stopPropagation(); onDownload(e) }}>
                      <Download className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 mt-1.5">
                <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-5 font-normal text-muted-foreground bg-transparent">
                  {artifact.file_type.toUpperCase()}
                </Badge>
                <span className="text-[10px] text-muted-foreground">
                  {formatBytes(artifact.size_bytes)}
                  {artifact.created_at && ` • ${formatDate(artifact.created_at)}`}
                </span>
              </div>
            </div>
          </div>
      )}
    </Card>
  )
}

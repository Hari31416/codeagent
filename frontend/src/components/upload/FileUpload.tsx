import { useCallback, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Paperclip, Loader2 } from 'lucide-react'

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void
  isUploading?: boolean
  progress?: number
  accept?: string
}

export function FileUpload({ 
  onFilesSelected, 
  isUploading, 
  progress = 0,
  accept = '.csv,.xlsx,.xls,.json,.png,.jpg,.jpeg,.gif,.py,.md,.txt'
}: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  const handleClick = useCallback(() => {
    inputRef.current?.click()
  }, [])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length > 0) {
      onFilesSelected(files)
    }
    // Reset input
    e.target.value = ''
  }, [onFilesSelected])

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={accept}
        onChange={handleChange}
        className="hidden"
      />
      <Button
        variant="outline"
        size="icon"
        onClick={handleClick}
        disabled={isUploading}
      >
        {isUploading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Paperclip className="h-4 w-4" />
        )}
      </Button>
      {isUploading && progress > 0 && (
        <span className="text-xs text-muted-foreground">
          {progress}%
        </span>
      )}
    </>
  )
}

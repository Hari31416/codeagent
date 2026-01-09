import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Download, ZoomIn, ZoomOut } from 'lucide-react'
import { useState } from 'react'

interface ImageArtifactProps {
  src: string
  alt: string
}

export function ImageArtifact({ src, alt }: ImageArtifactProps) {
  const [zoom, setZoom] = useState(1)

  const handleDownload = () => {
    const link = document.createElement('a')
    link.href = src
    link.download = alt
    link.click()
  }

  return (
    <Card className="p-2 h-full flex flex-col border-0 shadow-none">
      <div className="flex justify-end gap-2 mb-2 shrink-0">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setZoom(z => Math.max(0.25, z - 0.25))}
          className="h-8 w-8"
        >
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          onClick={() => setZoom(z => Math.min(3, z + 0.25))}
          className="h-8 w-8"
        >
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="icon" onClick={handleDownload} className="h-8 w-8">
          <Download className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex-1 overflow-auto flex items-center justify-center bg-muted/20 rounded border">
        <img
          src={src}
          alt={alt}
          style={{ transform: `scale(${zoom})`, transformOrigin: 'center' }}
          className="max-w-full max-h-full object-contain transition-transform"
        />
      </div>
    </Card>
  )
}

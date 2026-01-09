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
    <Card className="p-4">
      <div className="flex justify-end gap-2 mb-4">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setZoom(z => Math.max(0.25, z - 0.25))}
        >
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          onClick={() => setZoom(z => Math.min(3, z + 0.25))}
        >
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="icon" onClick={handleDownload}>
          <Download className="h-4 w-4" />
        </Button>
      </div>
      <div className="overflow-auto max-h-[600px]">
        <img
          src={src}
          alt={alt}
          style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}
          className="max-w-full transition-transform"
        />
      </div>
    </Card>
  )
}

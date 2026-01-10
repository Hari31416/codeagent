import { useState } from 'react'
import { ChevronRight, ChevronDown, Code2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CodeViewer } from '@/components/artifacts/CodeViewer'
import { cn } from '@/lib/utils'

interface CollapsibleCodeProps {
  code: string
  language?: string
  defaultOpen?: boolean
  label?: string
}

export function CollapsibleCode({ 
  code, 
  language = 'python',
  defaultOpen = false,
  label = 'Code'
}: CollapsibleCodeProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="mt-2 border rounded-md overflow-hidden bg-background">
      <Button
        variant="ghost"
        size="sm"
        className={cn(
          "w-full justify-start gap-2 h-8 rounded-none hover:bg-muted/50 font-normal",
          isOpen && "bg-muted/30"
        )}
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
        <Code2 className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">
          {label}
        </span>
      </Button>
      
      {isOpen && (
        <div className="border-t">
          <CodeViewer code={code} language={language} />
        </div>
      )}
    </div>
  )
}

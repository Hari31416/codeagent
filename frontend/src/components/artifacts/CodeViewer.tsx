import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Check, Copy } from 'lucide-react'
import { useState, useCallback } from 'react'

interface CodeViewerProps {
  code: string
  language?: string
}

export function CodeViewer({ code, language = 'python' }: CodeViewerProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [code])

  return (
    <Card className="relative">
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted">
        <span className="text-xs font-mono text-muted-foreground">
          {language}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={handleCopy}
        >
          {copied ? (
            <Check className="h-3 w-3 text-green-500" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
        </Button>
      </div>
      <pre className="p-4 overflow-auto max-h-[400px] text-sm">
        <code className="font-mono">{code}</code>
      </pre>
    </Card>
  )
}

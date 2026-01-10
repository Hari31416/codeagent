import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Check, Copy } from 'lucide-react'
import { useState, useCallback } from 'react'

import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

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
    <Card className="relative overflow-hidden border bg-[#1e1e1e] text-zinc-50">
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-700 bg-[#252526]">
        <span className="text-xs font-medium text-zinc-400 uppercase font-mono">
          {language}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-50"
          onClick={handleCopy}
        >
          {copied ? (
            <Check className="h-3 w-3 text-green-500" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
        </Button>
      </div>
      <div className="max-h-[400px] overflow-auto text-sm">
        <SyntaxHighlighter
          language={language.toLowerCase()}
          style={vscDarkPlus}
          customStyle={{
            margin: 0,
            padding: '1rem',
            background: 'transparent',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.875rem'
          }}
          wrapLines={true}
          wrapLongLines={true}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </Card>
  )
}

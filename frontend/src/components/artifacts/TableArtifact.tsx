import { useMemo, useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Copy, Download, Check } from 'lucide-react'

interface TableArtifactProps {
  content: string
  fileType: 'csv' | 'xlsx' | 'xls'
}

function parseCSV(content: string): { headers: string[]; rows: string[][] } {
  const lines = content.trim().split('\n')
  if (lines.length === 0) return { headers: [], rows: [] }
  
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
  const rows = lines.slice(1).map(line => 
    line.split(',').map(cell => cell.trim().replace(/^"|"$/g, ''))
  )
  
  return { headers, rows }
}

function formatCell(value: string): string {
  if (!isNaN(Number(value)) && value.trim() !== '') {
    const num = parseFloat(value)
    if (Number.isInteger(num)) return value
    return num.toFixed(2)
  }
  return value
}

export function TableArtifact({ content, fileType }: TableArtifactProps) {
  const [copied, setCopied] = useState(false)

  const { headers, rows } = useMemo(() => {
    if (fileType === 'csv') {
      return parseCSV(content)
    }
    // For Excel files, would need a proper parser
    // For now, assume content is already converted to CSV
    return parseCSV(content)
  }, [content, fileType])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'data.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (headers.length === 0) {
    return (
      <Card className="p-4 text-muted-foreground">
        No data to display
      </Card>
    )
  }

  return (
    <Card className="overflow-hidden flex flex-col">
      <div className="flex items-center justify-end gap-2 p-2 border-b bg-muted/20">
        <Button
          variant="outline"
          size="sm"
          onClick={handleCopy}
          className="h-8 text-xs gap-1.5"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? 'Copied' : 'Copy CSV'}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleDownload}
          className="h-8 text-xs gap-1.5"
        >
          <Download className="h-3.5 w-3.5" />
          Download
        </Button>
      </div>

      <div className="overflow-auto max-h-[500px]">
        <table className="w-full text-sm font-mono">
          <thead className="sticky top-0 bg-muted z-10 shadow-sm">
            <tr>
              {headers.map((header, i) => (
                <th
                  key={i} 
                  className="px-4 py-2.5 text-left font-semibold text-muted-foreground border-b select-none"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 100).map((row, i) => (
              <tr
                key={i}
                className="even:bg-muted/30 hover:bg-muted/50 transition-colors"
              >
                {row.map((cell, j) => (
                  <td key={j} className="px-4 py-2 border-b border-muted/20 whitespace-nowrap text-foreground/90">
                    {formatCell(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {rows.length > 100 && (
        <div className="p-2 text-center text-xs text-muted-foreground border-t bg-muted/20">
          Showing first 100 of {rows.length} rows
        </div>
      )}
    </Card>
  )
}

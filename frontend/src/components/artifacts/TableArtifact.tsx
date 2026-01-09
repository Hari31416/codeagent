import { useMemo } from 'react'
import { Card } from '@/components/ui/card'

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

export function TableArtifact({ content, fileType }: TableArtifactProps) {
  const { headers, rows } = useMemo(() => {
    if (fileType === 'csv') {
      return parseCSV(content)
    }
    // For Excel files, would need a proper parser
    // For now, assume content is already converted to CSV
    return parseCSV(content)
  }, [content, fileType])

  if (headers.length === 0) {
    return (
      <Card className="p-4 text-muted-foreground">
        No data to display
      </Card>
    )
  }

  return (
    <Card className="overflow-auto max-h-[500px]">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-muted">
          <tr>
            {headers.map((header, i) => (
              <th 
                key={i} 
                className="px-4 py-2 text-left font-medium border-b"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 100).map((row, i) => (
            <tr key={i} className="hover:bg-muted/50">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2 border-b whitespace-nowrap">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 100 && (
        <div className="p-2 text-center text-sm text-muted-foreground">
          Showing first 100 of {rows.length} rows
        </div>
      )}
    </Card>
  )
}

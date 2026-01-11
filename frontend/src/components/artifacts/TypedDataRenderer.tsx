import { CodeViewer } from './CodeViewer'
import { Card } from '@/components/ui/card'
import { Dialog, DialogContent, DialogTrigger, DialogTitle } from '@/components/ui/dialog'
import { ZoomIn } from 'lucide-react'
import type { TypedData } from '@/types/api'

interface TypedDataRendererProps {
    data: TypedData
    showAll?: boolean
}

export function TypedDataRenderer({ data, showAll = false }: TypedDataRendererProps) {
    if (!data) return null

    switch (data.kind) {
        case 'table':
            // The data.data is expected to be { headers: string[], rows: any[][] }
            // But TableArtifact expects raw CSV content or we need to adapt it
            // Let's adapt InlineTable here or use TableArtifact if we convert to CSV

            // For now, let's create a simple inline table renderer
            const tableData = data.data as { headers: string[], rows: any[][] }
            if (!tableData?.headers) return <div className="text-sm text-muted-foreground">Invalid table data</div>

            const formatCell = (value: any): string => {
                if (typeof value === 'number') {
                    if (Number.isInteger(value)) return String(value)
                    return value.toFixed(2)
                }
                const str = String(value)
                if (!isNaN(Number(str)) && str.trim() !== '') {
                    const num = parseFloat(str)
                    if (Number.isInteger(num)) return str
                    return num.toFixed(2)
                }
                return str
            }

            // Determine rendering limit
            const ROW_LIMIT = 50
            const shouldTruncate = !showAll && tableData.rows.length > ROW_LIMIT
            const displayRows = shouldTruncate ? tableData.rows.slice(0, ROW_LIMIT) : tableData.rows

            return (
                <Card className={`overflow-auto my-2 ${showAll ? 'max-h-[800px]' : 'max-h-[400px]'}`}>
                    <table className="w-full text-sm font-mono">
                        <thead className="sticky top-0 bg-muted z-10 shadow-sm">
                            <tr>
                                {tableData.headers.map((header, i) => (
                                    <th key={i} className="px-4 py-2.5 text-left font-semibold text-muted-foreground border-b select-none">
                                        {header}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {displayRows.map((row, i) => (
                                <tr key={i} className="even:bg-muted/30 hover:bg-muted/50 transition-colors">
                                    {row.map((cell, j) => (
                                        <td key={j} className="px-4 py-2 border-b border-muted/20 whitespace-nowrap text-foreground/90">
                                            {formatCell(cell)}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <div className="p-2 text-xs text-center text-muted-foreground border-t bg-muted/20">
                        {data.metadata?.rows ? `${data.metadata.rows} rows` : ''}
                        {shouldTruncate ? ` (showing first ${ROW_LIMIT})` : ''}
                    </div>
                </Card>
            )

        case 'image':
            const imageUrl = `data:image/${data.metadata?.format || 'png'};base64,${data.data}`
            return (
                <Dialog>
                    <DialogTrigger asChild>
                        <Card className="p-2 my-2 inline-block cursor-zoom-in hover:ring-2 hover:ring-primary/50 transition-all group relative overflow-hidden">
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100 z-10">
                                <ZoomIn className="text-white drop-shadow-md w-8 h-8" />
                            </div>
                            <img
                                src={imageUrl}
                                alt="Generated output"
                                className="max-h-[500px] max-w-full rounded"
                            />
                        </Card>
                    </DialogTrigger>
                    <DialogContent className="max-w-[90vw] max-h-[90vh] w-fit p-0 border-none bg-transparent shadow-none overflow-hidden flex items-center justify-center">
                        <div className="sr-only">
                            <DialogTitle>Image Preview</DialogTitle>
                        </div>
                        <img
                            src={imageUrl}
                            alt="Full screen preview"
                            className="max-w-full max-h-[90vh] rounded-md shadow-2xl"
                        />
                    </DialogContent>
                </Dialog>
            )

        case 'plotly':
            return (
                <Card className="p-4 my-2">
                    <div className="text-sm text-muted-foreground">Interactive plot (visualization not fully implemented in preview)</div>
                    <pre className="text-xs overflow-auto max-h-[200px] mt-2">
                        {JSON.stringify(data.data, null, 2)}
                    </pre>
                </Card>
            )

        case 'json':
            return <CodeViewer code={JSON.stringify(data.data, null, 2)} language="json" />

        case 'multi':
            // Handle multiple items (e.g., tuple of DataFrames or dict of DataFrames)
            const multiData = data.data as Array<TypedData & { metadata?: { index?: number; name?: string } }>
            if (!Array.isArray(multiData)) return null

            const hasNames = data.metadata?.has_names as boolean

            return (
                <div className="space-y-4">
                    <div className="text-xs text-muted-foreground">
                        Multiple outputs ({(data.metadata?.count as number) || multiData.length} items)
                    </div>
                    {multiData.map((item, i) => {
                        // Use name from metadata if available (dict case), otherwise use index
                        const label = hasNames && item.metadata?.name
                            ? item.metadata.name
                            : `Output ${(item.metadata?.index ?? i) + 1}`

                        return (
                            <div key={i} className="border-l-2 border-primary/30 pl-3">
                                <div className="text-xs font-medium text-muted-foreground mb-1">
                                    {label}
                                </div>
                                <TypedDataRenderer data={item} />
                            </div>
                        )
                    })}
                </div>
            )

        case 'text':
        default:
            if (!data.data) return null
            return <pre className="whitespace-pre-wrap text-sm my-1">{String(data.data)}</pre>
    }
}

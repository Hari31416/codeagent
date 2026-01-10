import { CodeViewer } from './CodeViewer'
import { Card } from '@/components/ui/card'
import type { TypedData } from '@/types/api'

interface TypedDataRendererProps {
    data: TypedData
}

export function TypedDataRenderer({ data }: TypedDataRendererProps) {
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

            return (
                <Card className="overflow-auto max-h-[400px] my-2">
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
                            {tableData.rows.slice(0, 50).map((row, i) => (
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
                        {tableData.rows.length > 50 ? ' (showing first 50)' : ''}
                    </div>
                </Card>
            )

        case 'image':
            return (
                <Card className="p-2 my-2 inline-block">
                    <img
                        src={`data:image/${data.metadata?.format || 'png'};base64,${data.data}`}
                        alt="Generated output"
                        className="max-h-[500px] max-w-full rounded"
                    />
                </Card>
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

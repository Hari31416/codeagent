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

            return (
                <Card className="overflow-auto max-h-[400px] my-2">
                    <table className="w-full text-sm">
                        <thead className="sticky top-0 bg-muted">
                            <tr>
                                {tableData.headers.map((header, i) => (
                                    <th key={i} className="px-4 py-2 text-left font-medium border-b">
                                        {header}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {tableData.rows.slice(0, 50).map((row, i) => (
                                <tr key={i} className="hover:bg-muted/50">
                                    {row.map((cell, j) => (
                                        <td key={j} className="px-4 py-2 border-b whitespace-nowrap">
                                            {String(cell)}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <div className="p-2 text-xs text-muted-foreground">
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

        case 'text':
        default:
            if (!data.data) return null
            return <pre className="whitespace-pre-wrap text-sm my-1">{String(data.data)}</pre>
    }
}

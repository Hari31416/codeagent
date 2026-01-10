import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Download, FileText, FileJson, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import html2pdf from 'html2pdf.js'
// Use a direct highlight.js style import that's definitely available
import 'highlight.js/styles/github.css'

interface ExportModalProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    exportData: {
        metadata: Record<string, unknown>
        markdown: string
        filename: string
    } | null
    isLoading?: boolean
}

export function ExportModal({ open, onOpenChange, exportData, isLoading = false }: ExportModalProps) {
    const [isPdfGenerating, setIsPdfGenerating] = useState(false)

    const handleDownloadMarkdown = () => {
        if (!exportData) return

        const blob = new Blob([exportData.markdown], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = exportData.filename
        a.click()
        URL.revokeObjectURL(url)
    }

    const handleDownloadJSON = () => {
        if (!exportData) return

        const blob = new Blob([JSON.stringify(exportData.metadata, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = exportData.filename.replace('.md', '.json')
        a.click()
        URL.revokeObjectURL(url)
    }

    const handleExportPDF = async () => {
        if (!exportData) return

        setIsPdfGenerating(true)
        try {
            const element = document.getElementById('markdown-preview-content')
            if (!element) {
                throw new Error('Preview content not found')
            }

            const opt = {
                margin: 0.5,
                filename: exportData.filename.replace('.md', '.pdf'),
                image: { type: 'jpeg' as const, quality: 0.98 },
                html2canvas: {
                    scale: 2,
                    useCORS: true,
                    onclone: (clonedDoc: Document) => {
                        // Aggressively fix oklch color issue for html2canvas
                        // 1. Completely clear head
                        const head = clonedDoc.head;
                        while (head.firstChild) {
                            head.removeChild(head.firstChild);
                        }

                        // 2. Add safe styles for the PDF
                        const style = clonedDoc.createElement('style')
                        style.innerHTML = `
                            body { 
                                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
                                background-color: #ffffff !important;
                                color: #0f172a !important;
                                margin: 0 !important;
                                padding: 0 !important;
                            }
                            #markdown-preview-content {
                                padding: 20px !important;
                                width: 100% !important;
                                color: #0f172a !important;
                                background-color: #ffffff !important;
                            }
                            h1 { font-size: 20pt; margin: 20pt 0 10pt; font-weight: bold; border-bottom: 1px solid #e2e8f0; padding-bottom: 5pt; }
                            h2 { font-size: 16pt; margin: 15pt 0 8pt; font-weight: bold; border-bottom: 1px solid #e2e8f0; padding-bottom: 3pt; }
                            h3 { font-size: 14pt; margin: 12pt 0 6pt; font-weight: bold; }
                            h4 { font-size: 12pt; margin: 10pt 0 5pt; font-weight: bold; }
                            p { margin: 0 0 10pt; line-height: 1.5; font-size: 10.5pt; }
                            
                            /* Ensure code blocks wrap and have highlighting style */
                            pre { 
                                background-color: #f1f5f9 !important; 
                                border: 1px solid #e2e8f0 !important;
                                border-radius: 4px !important;
                                padding: 10pt !important;
                                margin: 10pt 0 !important;
                                white-space: pre-wrap !important;
                                word-wrap: break-word !important;
                                overflow-wrap: break-word !important;
                            }
                            code { 
                                font-family: "JetBrains Mono", Menlo, Monaco, Consolas, "Courier New", monospace !important;
                                font-size: 9pt !important;
                                color: #0f172a !important;
                                background-color: #f1f5f9 !important;
                                padding: 2pt 4pt !important;
                                border-radius: 3pt !important;
                            }
                            pre code {
                                padding: 0 !important;
                                background-color: transparent !important;
                            }

                            /* Table styling */
                            table {
                                border-collapse: collapse !important;
                                width: 100% !important;
                                margin: 10pt 0 !important;
                                font-size: 9pt !important;
                            }
                            th, td {
                                border: 1px solid #e2e8f0 !important;
                                padding: 6pt 8pt !important;
                                text-align: left !important;
                            }
                            th {
                                background-color: #f8fafc !important;
                                font-weight: bold !important;
                            }

                            /* Image handling */
                            img {
                                max-width: 100% !important;
                                height: auto !important;
                                margin: 10pt 0 !important;
                            }

                            /* Highlight.js fallbacks for PDF */
                            .hljs-comment, .hljs-quote { color: #64748b; }
                            .hljs-keyword, .hljs-selector-tag { color: #0550ae; }
                            .hljs-string, .hljs-attr { color: #0a3069; }
                            .hljs-number, .hljs-literal { color: #0550ae; }
                            .hljs-function, .hljs-title { color: #8250df; }
                            .hljs-operator { color: #0550ae; }
                        `
                        head.appendChild(style)

                        // 3. Remove all classes that might have tailwind oklch stuff attached
                        // and set basic layout classes
                        const content = clonedDoc.getElementById('markdown-preview-content')
                        if (content) {
                            content.className = '' // Clear all tailwind classes
                            content.style.backgroundColor = '#ffffff'
                            content.style.color = '#0f172a'
                        }
                    }
                },
                jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' as const }
            }

            await html2pdf().set(opt).from(element).save()
        } catch (error) {
            console.error('Failed to generate PDF:', error)
        } finally {
            setIsPdfGenerating(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle>Export Chat</DialogTitle>
                    <DialogDescription>
                        Preview and download your chat in multiple formats
                    </DialogDescription>
                </DialogHeader>

                {isLoading ? (
                    <div className="flex-1 flex items-center justify-center py-12">
                        <div className="flex flex-col items-center gap-3">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                            <p className="text-sm text-muted-foreground">Preparing export...</p>
                        </div>
                    </div>
                ) : exportData ? (
                    <>
                        <div className="flex gap-2 py-2 border-b">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleDownloadMarkdown}
                                className="gap-2"
                            >
                                <FileText className="h-4 w-4" />
                                Download Markdown
                            </Button>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleDownloadJSON}
                                className="gap-2"
                            >
                                <FileJson className="h-4 w-4" />
                                Download JSON
                            </Button>
                            <Button
                                variant="default"
                                size="sm"
                                onClick={handleExportPDF}
                                disabled={isPdfGenerating}
                                className="gap-2"
                            >
                                {isPdfGenerating ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        Generating...
                                    </>
                                ) : (
                                    <>
                                        <Download className="h-4 w-4" />
                                        Export as PDF
                                    </>
                                )}
                            </Button>
                        </div>

                        <div
                            id="markdown-preview-content"
                            className="flex-1 overflow-y-auto prose prose-slate prose-sm max-w-none p-8 bg-white text-slate-900 rounded-md shadow-inner border"
                            style={{
                                // Fallback styles in case prose is not fully active
                                fontSize: '14px',
                                lineHeight: '1.6',
                            }}
                        >
                            <style dangerouslySetInnerHTML={{
                                __html: `
                                #markdown-preview-content h1 { font-size: 1.5rem; font-weight: 700; margin-top: 1.5rem; margin-bottom: 1rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; }
                                #markdown-preview-content h2 { font-size: 1.25rem; font-weight: 700; margin-top: 1.25rem; margin-bottom: 0.75rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.25rem; }
                                #markdown-preview-content h3 { font-size: 1.125rem; font-weight: 700; margin-top: 1rem; margin-bottom: 0.5rem; }
                                #markdown-preview-content p { margin-bottom: 1rem; }
                                #markdown-preview-content table { border-collapse: collapse; width: 100%; margin-bottom: 1rem; border: 1px solid #e2e8f0; }
                                #markdown-preview-content th, #markdown-preview-content td { border: 1px solid #e2e8f0; padding: 0.5rem 0.75rem; text-align: left; }
                                #markdown-preview-content th { background-color: #f8fafc; font-weight: 600; }
                                #markdown-preview-content pre { padding: 1rem; border-radius: 0.375rem; margin-bottom: 1rem; overflow-x: auto; }
                            `}} />
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                rehypePlugins={[rehypeHighlight]}
                                urlTransform={(url) => {
                                    if (url.startsWith('data:')) return url
                                    return url
                                }}
                                components={{
                                    img: ({ node, ...props }) => (
                                        <img
                                            {...props}
                                            className="max-w-full h-auto rounded-md shadow-sm border my-4 bg-white"
                                            loading="lazy"
                                        />
                                    )
                                }}
                            >
                                {exportData.markdown}
                            </ReactMarkdown>
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex items-center justify-center py-12">
                        <p className="text-sm text-muted-foreground">No export data available</p>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    )
}

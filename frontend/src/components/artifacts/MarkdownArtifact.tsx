import { Card } from '@/components/ui/card'

interface MarkdownArtifactProps {
  content: string
}

export function MarkdownArtifact({ content }: MarkdownArtifactProps) {
  // For a full implementation, use a markdown parser like 'marked' or 'react-markdown'
  // This is a simple fallback
  return (
    <Card className="p-4 prose prose-sm max-w-none dark:prose-invert">
      <pre className="whitespace-pre-wrap">{content}</pre>
    </Card>
  )
}

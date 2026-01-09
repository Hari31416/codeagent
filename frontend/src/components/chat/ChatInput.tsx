import { useState, useCallback, type KeyboardEvent } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Send } from 'lucide-react'

interface ChatInputProps {
    onSend: (content: string) => void
    disabled?: boolean
    placeholder?: string
}

export function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
    const [value, setValue] = useState('')

    const handleSend = useCallback(() => {
        const trimmed = value.trim()
        if (trimmed && !disabled) {
            onSend(trimmed)
            setValue('')
        }
    }, [value, onSend, disabled])

    const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }, [handleSend])

    return (
        <div className="flex gap-2 flex-1">
            <Textarea
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder || 'Type your message...'}
                disabled={disabled}
                className="min-h-[44px] max-h-[200px] resize-none"
                rows={1}
            />
            <Button
                onClick={handleSend}
                disabled={disabled || !value.trim()}
                size="icon"
            >
                <Send className="h-4 w-4" />
            </Button>
        </div>
    )
}

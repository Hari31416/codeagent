import { useState, useCallback, type KeyboardEvent } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Send } from 'lucide-react'
import { ModelSelector } from './ModelSelector'

interface ChatInputProps {
    onSend: (content: string) => void
    disabled?: boolean
    placeholder?: string
    selectedModel?: string
    onModelChange?: (model: string) => void
    actions?: React.ReactNode
}

export function ChatInput({
    onSend,
    disabled,
    placeholder,
    selectedModel,
    onModelChange,
    actions
}: ChatInputProps) {
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
        <div className="flex flex-col w-full border rounded-xl bg-background focus-within:ring-1 focus-within:ring-ring transition-all overflow-hidden shadow-sm">
            <Textarea
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder || 'Type your message...'}
                disabled={disabled}
                className="min-h-[60px] max-h-[400px] w-full resize-none border-0 focus-visible:ring-0 px-4 py-3 bg-transparent text-base"
            />

            <div className="flex items-center justify-between px-2 py-2 border-t bg-muted/20">
                <div className="flex items-center gap-1">
                    {actions}
                    {onModelChange && (
                        <ModelSelector
                            value={selectedModel}
                            onValueChange={onModelChange}
                            disabled={disabled}
                        />
                    )}
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        onClick={handleSend}
                        disabled={disabled || !value.trim()}
                        size="sm"
                        className="h-8 w-8 p-0 rounded-lg"
                    >
                        <Send className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
    )
}

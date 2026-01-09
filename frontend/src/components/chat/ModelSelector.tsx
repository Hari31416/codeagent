import { useEffect, useState, type KeyboardEvent } from 'react'
import {
    Select,
    SelectContent,
    SelectGroup,
    SelectItem,
    SelectLabel,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { getAvailableModels } from '@/api/models'
import type { ModelInfo } from '@/types/api'
import { Bot, Sparkles, Pencil, X, Check } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ModelSelectorProps {
    value?: string
    onValueChange: (value: string) => void
    disabled?: boolean
}

export function ModelSelector({ value, onValueChange, disabled }: ModelSelectorProps) {
    const [models, setModels] = useState<ModelInfo[]>([])
    const [loading, setLoading] = useState(true)
    const [isCustom, setIsCustom] = useState(false)
    const [customValue, setCustomValue] = useState('')
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        getAvailableModels()
            .then(setModels)
            .catch(console.error)
            .finally(() => setLoading(false))
    }, [])

    // Check if current value is NOT in the predefined list (and not empty/default)
    useEffect(() => {
        if (value && value !== 'default' && models.length > 0) {
            const isKnown = models.some(m => m.slug === value)
            if (!isKnown) {
                setIsCustom(true)
                setCustomValue(value)
            } else {
                setIsCustom(false)
            }
        }
    }, [value, models])

    const handleCustomSubmit = () => {
        if (!customValue.trim()) return

        if (!customValue.startsWith('openrouter/')) {
            setError('Must start with openrouter/')
            return
        }

        setError(null)
        onValueChange(customValue)
        // Keep isCustom true to show input
    }

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            e.preventDefault()
            handleCustomSubmit()
        }
    }

    // Group models by provider
    const groupedModels = models.reduce((acc, model) => {
        if (!acc[model.provider]) {
            acc[model.provider] = []
        }
        acc[model.provider].push(model)
        return acc
    }, {} as Record<string, ModelInfo[]>)

    if (isCustom) {
        return (
            <div className="flex items-center gap-1">
                <div className="relative">
                    <Input
                        value={customValue}
                        onChange={(e) => {
                            setCustomValue(e.target.value)
                            if (error) setError(null)
                        }}
                        onKeyDown={handleKeyDown}
                        placeholder="openrouter/..."
                        className={cn(
                            "w-[200px] h-[44px] pr-8",
                            error && "border-red-500 focus-visible:ring-red-500"
                        )}
                        disabled={disabled}
                    />
                    <Button
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-0 h-full w-8 hover:bg-transparent"
                        onClick={handleCustomSubmit}
                        disabled={disabled}
                    >
                        <Check className="h-3 w-3 text-muted-foreground" />
                    </Button>
                </div>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                        setIsCustom(false)
                        setCustomValue('')
                        onValueChange('') // Reset to default/empty
                    }}
                    title="Back to list"
                >
                    <X className="h-4 w-4" />
                </Button>
                {error && (
                    <div className="absolute top-12 left-0 z-50 bg-destructive text-destructive-foreground text-xs px-2 py-1 rounded shadow-md">
                        {error}
                    </div>
                )}
            </div>
        )
    }

    return (
        <Select
            value={value}
            onValueChange={(val) => {
                if (val === 'custom') {
                    setIsCustom(true)
                    setCustomValue('')
                } else {
                    onValueChange(val)
                }
            }}
            disabled={disabled || loading}
        >
            <SelectTrigger className="w-[180px] h-[44px]">
                <div className="flex items-center gap-2 overflow-hidden">
                    <Bot className="h-4 w-4 shrink-0" />
                    <SelectValue placeholder="Select Model" />
                </div>
            </SelectTrigger>
            <SelectContent>
                {!value && (
                    <SelectItem value="default">
                        <div className="flex items-center gap-2">
                            <Sparkles className="h-4 w-4 text-yellow-500" />
                            <span>Default (Auto)</span>
                        </div>
                    </SelectItem>
                )}

                {Object.entries(groupedModels).map(([provider, models]) => (
                    <SelectGroup key={provider}>
                        <SelectLabel>{provider}</SelectLabel>
                        {models.map((model) => (
                            <SelectItem key={model.slug} value={model.slug}>
                                <div className="flex flex-col items-start text-sm">
                                    <span className="font-medium">{model.name}</span>
                                    {model.description && (
                                        <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                                            {model.description}
                                        </span>
                                    )}
                                </div>
                            </SelectItem>
                        ))}
                    </SelectGroup>
                ))}

                <SelectGroup>
                    <SelectLabel>Other</SelectLabel>
                    <SelectItem value="custom">
                        <div className="flex items-center gap-2">
                            <Pencil className="h-3 w-3" />
                            <span>Custom Model...</span>
                        </div>
                    </SelectItem>
                </SelectGroup>
            </SelectContent>
        </Select>
    )
}

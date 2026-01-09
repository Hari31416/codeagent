import type { ModelInfo } from '@/types/api'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8011/api/v1'

export async function getAvailableModels(): Promise<ModelInfo[]> {
  const response = await fetch(`${API_BASE_URL}/models`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch models: ${response.statusText}`)
  }
  
  return response.json()
}

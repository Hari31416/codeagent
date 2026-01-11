import type { ModelInfo } from '@/types/api'
import { getAuthHeaders, handleAuthError } from './client'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8011/api/v1'

export async function getAvailableModels(): Promise<ModelInfo[]> {
  const response = await fetch(`${API_BASE_URL}/models`, {
    headers: getAuthHeaders(),
  })
  
  if (!response.ok) {
    handleAuthError(response.status)
    throw new Error(`Failed to fetch models: ${response.statusText}`)
  }
  
  return response.json()
}

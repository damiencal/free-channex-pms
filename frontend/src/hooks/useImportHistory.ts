import { useQuery } from '@tanstack/react-query'

export interface ImportRun {
  id: number
  platform: string
  filename: string
  inserted_count: number
  updated_count: number
  skipped_count: number
  imported_at: string
}

export function useImportHistory(limit = 10) {
  return useQuery<ImportRun[]>({
    queryKey: ['ingestion', 'history', limit],
    queryFn: async () => {
      const response = await fetch(`/ingestion/history?limit=${limit}`)
      if (!response.ok) {
        throw new Error(`Failed to fetch import history: ${response.statusText}`)
      }
      return response.json()
    },
    staleTime: 60_000,
  })
}

import { useQuery } from '@tanstack/react-query'
import { documentsApi } from '@/api/documents'

export function useDocuments() {
  return useQuery({
    queryKey: ['queue'],
    queryFn: documentsApi.getQueue,
    refetchInterval: 5000,
  })
}

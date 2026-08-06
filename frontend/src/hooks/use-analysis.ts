import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { DocumentAnalysis, ClauseAnalysis } from '@/types/analysis';
import { APIResponse } from '@/types/api';

export function useDocumentSummary(documentId: string, enabled: boolean = true, isAnalyzing: boolean = false) {
  return useQuery({
    queryKey: ['analysis', documentId, 'summary'],
    queryFn: async () => {
      const response = await apiClient.get<APIResponse<DocumentAnalysis>>(`/analysis/${documentId}/summary`);
      return response.data.data;
    },
    enabled: !!documentId && enabled,
    retry: false, // Don't retry on error, just wait for next poll
    // Refetch every 5s while the summary isn't loaded yet, or while analyzing
    refetchInterval: (query) => {
      if (isAnalyzing || (!query.state.data && !query.state.error)) {
        return 5000;
      }
      return false;
    },
  });
}

export function useClauseAnalyses(documentId: string, enabled: boolean = true, isAnalyzing: boolean = false) {
  return useQuery({
    queryKey: ['analysis', documentId, 'clauses'],
    queryFn: async () => {
      const response = await apiClient.get<APIResponse<ClauseAnalysis[]>>(`/analysis/${documentId}/clauses`);
      return response.data.data;
    },
    enabled: !!documentId && enabled,
    retry: false,
    // Refetch every 5s while clauses aren't loaded yet, or while analyzing (to stream in new clauses)
    refetchInterval: (query) => {
      if (isAnalyzing || (!query.state.data && !query.state.error)) {
        return 5000;
      }
      return false;
    },
  });
}

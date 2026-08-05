import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { DocumentAnalysis, ClauseAnalysis } from '@/types/analysis';
import { APIResponse } from '@/types/api';

export function useDocumentSummary(documentId: string) {
  return useQuery({
    queryKey: ['analysis', documentId, 'summary'],
    queryFn: async () => {
      const response = await apiClient.get<APIResponse<DocumentAnalysis>>(`/analysis/${documentId}/summary`);
      return response.data.data;
    },
    enabled: !!documentId,
    retry: 1, // Don't retry much if it's not ready yet
  });
}

export function useClauseAnalyses(documentId: string) {
  return useQuery({
    queryKey: ['analysis', documentId, 'clauses'],
    queryFn: async () => {
      const response = await apiClient.get<APIResponse<ClauseAnalysis[]>>(`/analysis/${documentId}/clauses`);
      return response.data.data;
    },
    enabled: !!documentId,
    retry: 1,
  });
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { Document, DocumentType } from '@/types/document';
import type { AnalysisStatus } from '@/types/analysis';
import { PaginatedResponse, APIResponse } from '@/types/api';

export function useDocuments(page = 1, pageSize = 10) {
  return useQuery({
    queryKey: ['documents', page, pageSize],
    queryFn: async () => {
      const response = await apiClient.get<APIResponse<PaginatedResponse<Document>>>('/documents/', {
        params: { page, page_size: pageSize },
      });
      return response.data.data;
    },
    refetchInterval: (query) => {
      const items = query.state.data?.items;
      const hasActive = items?.some(
        (d) =>
          d.status === 'uploaded' ||
          d.status === 'extracting' ||
          d.status === 'segmenting' ||
          d.status === 'analyzing'
      );
      return hasActive ? 3000 : false;
    },
    refetchIntervalInBackground: true,
  });
}

export function useDocument(id: string) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: ['documents', id],
    queryFn: async () => {
      const response = await apiClient.get<APIResponse<Document>>(`/documents/${id}`);
      return response.data.data;
    },
    enabled: !!id,
    placeholderData: () => {
      // Instantly hydrate from documents list cache if available
      const queries = queryClient.getQueriesData<APIResponse<PaginatedResponse<Document>>>({
        queryKey: ['documents'],
      });
      for (const [, queryData] of queries) {
        const found = queryData?.data?.items?.find((d) => d.id === id);
        if (found) return found;
      }
      return undefined;
    },
    staleTime: 5 * 60 * 1000,
    refetchIntervalInBackground: true,
    retry: 3,
    refetchInterval: (query) => {
      const doc = query.state.data;
      if (
        !doc ||
        doc.status === 'uploaded' ||
        doc.status === 'extracting' ||
        doc.status === 'segmenting' ||
        doc.status === 'analyzing'
      ) {
        return 3000; // poll every 3 seconds
      }
      return false;
    },
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      file,
      documentType,
      jurisdiction,
    }: {
      file: File;
      documentType: DocumentType | string;
      jurisdiction?: string;
    }) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('document_type', documentType);
      if (jurisdiction) {
        formData.append('jurisdiction', jurisdiction);
      }

      try {
        const response = await apiClient.post<APIResponse<Document>>('/documents/upload', formData);
        return response.data.data;
      } catch (err: unknown) {
        const axiosErr = err as { response?: { data?: { detail?: string; message?: string } }; message?: string };
        const detail = axiosErr?.response?.data?.detail || axiosErr?.response?.data?.message || axiosErr?.message || "Failed to upload document.";
        throw new Error(detail);
      }
    },
    onSuccess: (data) => {
      if (data?.id) {
        queryClient.setQueryData(['documents', data.id], data);
      }
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/documents/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useResumeDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await apiClient.post<APIResponse<AnalysisStatus>>(`/documents/${id}/resume`);
      return response.data.data;
    },
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['documents', id] });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['clause-analyses', id] });
    },
  });
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Document, DocumentType, DocumentStatus } from '@/types/document';
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
  });
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: ['documents', id],
    queryFn: async () => {
      const response = await apiClient.get<APIResponse<Document>>(`/documents/${id}`);
      return response.data.data;
    },
    enabled: !!id,
    // Poll if status is uploading, extracting, segmenting, or analyzing
    refetchInterval: (query) => {
      const doc = query.state.data;
      if (
        doc &&
        (doc.status === DocumentStatus.UPLOADED ||
          doc.status === DocumentStatus.EXTRACTING ||
          doc.status === DocumentStatus.SEGMENTING ||
          doc.status === DocumentStatus.ANALYZING)
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

      const response = await apiClient.post<APIResponse<Document>>('/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data.data;
    },
    onSuccess: () => {
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

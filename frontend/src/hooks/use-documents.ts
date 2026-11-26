import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { closeDocumentStream } from "@/lib/sse-registry";
import type { Document, DocumentType } from "@/types/document";
import type { AnalysisStatus } from "@/types/analysis";
import { PaginatedResponse, APIResponse } from "@/types/api";

const ACTIVE_DOCUMENT_STATUSES = new Set([
  "uploaded",
  "queued",
  "running",
  "extracting",
  "segmenting",
  "classifying",
  "embedding",
  "analyzing",
  "scoring",
  "summarizing",
  "cancelling",
]);

export function isActiveDocumentStatus(status?: string | null): boolean {
  if (!status) return false;
  return ACTIVE_DOCUMENT_STATUSES.has(status.trim().toLowerCase().replace(/_/g, " "));
}

export function useDocuments(page = 1, pageSize = 10) {
  return useQuery({
    queryKey: ["documents", page, pageSize],
    queryFn: async () => {
      const response = await apiClient.get<APIResponse<PaginatedResponse<Document>>>(
        "/documents/",
        {
          params: { page, page_size: pageSize },
        }
      );
      return response.data.data;
    },
    refetchInterval: (query) => {
      const items = query.state.data?.items;
      const hasActive = items?.some((d) => isActiveDocumentStatus(d.status));
      return hasActive ? 2500 : false;
    },
    refetchIntervalInBackground: true,
  });
}

export function useDocument(id: string) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: ["documents", id],
    queryFn: async () => {
      const response = await apiClient.get<APIResponse<Document>>(`/documents/${id}`);
      return response.data.data;
    },
    enabled: !!id,
    placeholderData: () => {
      // Instantly hydrate from documents list cache if available
      const queries = queryClient.getQueriesData<PaginatedResponse<Document>>({
        queryKey: ["documents"],
      });
      for (const [, queryData] of queries) {
        const found = queryData?.items?.find((d) => d.id === id);
        if (found) return found;
      }
      return undefined;
    },
    staleTime: 5 * 60 * 1000,
    refetchIntervalInBackground: true,
    retry: 2,
    refetchInterval: (query) => {
      const doc = query.state.data;
      if (!doc || isActiveDocumentStatus(doc.status)) {
        return 2500;
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
      formData.append("file", file);
      formData.append("document_type", documentType);
      if (jurisdiction) {
        formData.append("jurisdiction", jurisdiction);
      }

      try {
        const response = await apiClient.post<APIResponse<Document>>("/documents/upload", formData);
        return response.data.data;
      } catch (err: unknown) {
        const axiosErr = err as {
          response?: { data?: { detail?: string; message?: string } };
          message?: string;
        };
        const detail =
          axiosErr?.response?.data?.detail ||
          axiosErr?.response?.data?.message ||
          axiosErr?.message ||
          "Failed to upload document.";
        throw new Error(detail);
      }
    },
    onSuccess: (data) => {
      if (data?.id) {
        queryClient.setQueryData(["documents", data.id], data);
      }
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      // Mark deleting / cancelling optimistically across document caches while backend confirms
      await queryClient.cancelQueries({ queryKey: ["documents", id] });
      await queryClient.cancelQueries({ queryKey: ["analysis", id] });
      await apiClient.delete(`/documents/${id}`);
      return id;
    },
    onSuccess: (id) => {
      // 1. Close active SSE stream so zero further progress events arrive
      closeDocumentStream(id);

      // 2. Immediately remove item from cached document list pages
      queryClient.setQueriesData<PaginatedResponse<Document>>(
        { queryKey: ["documents"] },
        (oldData) => {
          if (!oldData || !Array.isArray(oldData.items)) return oldData;
          return {
            ...oldData,
            items: oldData.items.filter((doc) => doc.id !== id),
            total: Math.max(0, (oldData.total || oldData.items.length) - 1),
          };
        }
      );

      // 3. Remove all related document & analysis TanStack Query caches
      queryClient.removeQueries({ queryKey: ["documents", id] });
      queryClient.removeQueries({ queryKey: ["analysis", id] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
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
      queryClient.invalidateQueries({ queryKey: ["documents", id] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["analysis", id, "clauses"] });
      queryClient.invalidateQueries({ queryKey: ["analysis", id, "status"] });
      queryClient.invalidateQueries({ queryKey: ["analysis", id, "summary"] });
    },
  });
}

"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { API_BASE_URL } from "@/lib/constants";
import { registerDocumentStream } from "@/lib/sse-registry";
import type { AnalysisStatus, ClauseAnalysis, DocumentAnalysis } from "@/types/analysis";
import type { APIResponse } from "@/types/api";
import type { Document } from "@/types/document";

const ACTIVE_JOB_STATUSES = new Set([
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

export function useAnalysisStatus(documentId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ["analysis", documentId, "status"],
    queryFn: async () => {
      const response = await apiClient.get<APIResponse<AnalysisStatus>>(
        `/documents/${documentId}/status`
      );
      return response.data.data;
    },
    enabled: !!documentId && enabled,
    retry: 1,
    refetchInterval: (query) => {
      const st = String(query.state.data?.status || "").toLowerCase();
      if (!st || ACTIVE_JOB_STATUSES.has(st)) {
        return 2500;
      }
      return false;
    },
    refetchIntervalInBackground: true,
  });
}

export function useDocumentSummary(
  documentId: string,
  enabled: boolean = true,
  isPolling: boolean = false
) {
  return useQuery({
    queryKey: ["analysis", documentId, "summary"],
    queryFn: async () => {
      const response = await apiClient.get<APIResponse<DocumentAnalysis>>(
        `/analysis/${documentId}/summary`
      );
      return response.data.data;
    },
    enabled: !!documentId && enabled,
    retry: false,
    staleTime: 5 * 60 * 1000,
    refetchInterval: (query) => {
      if (isPolling || (!query.state.data && !query.state.error)) {
        return 3000;
      }
      return false;
    },
  });
}

export function useClauseAnalyses(
  documentId: string,
  enabled: boolean = true,
  isAnalyzing: boolean = false
) {
  return useQuery({
    queryKey: ["analysis", documentId, "clauses"],
    queryFn: async () => {
      const response = await apiClient.get<APIResponse<ClauseAnalysis[]>>(
        `/analysis/${documentId}/clauses`
      );
      return response.data.data;
    },
    enabled: !!documentId && enabled,
    retry: false,
    staleTime: 5 * 60 * 1000,
    refetchInterval: (query) => {
      if (isAnalyzing || (!query.state.data && !query.state.error)) {
        return 2500;
      }
      return false;
    },
  });
}

export function useAnalysisStream(documentId: string, enabled: boolean) {
  const queryClient = useQueryClient();
  const [isProvisional, setIsProvisional] = useState(false);

  useEffect(() => {
    if (!documentId || !enabled) return;

    const controller = new AbortController();
    const unregister = registerDocumentStream(documentId, controller);
    let stopped = false;

    const applyStatusPatch = (patch: Partial<AnalysisStatus>) => {
      queryClient.setQueryData<AnalysisStatus | undefined>(
        ["analysis", documentId, "status"],
        (prev) => ({
          document_id: documentId,
          status: prev?.status || "analyzing",
          progress: prev?.progress ?? 0.5,
          current_step: prev?.current_step ?? null,
          total_clauses: prev?.total_clauses ?? 0,
          analyzed_clauses: prev?.analyzed_clauses ?? 0,
          message: prev?.message ?? null,
          job_id: prev?.job_id ?? null,
          job_status: prev?.job_status ?? "running",
          stage: prev?.stage ?? null,
          ...prev,
          ...patch,
        })
      );

      if (patch.status) {
        queryClient.setQueryData<Document | undefined>(
          ["documents", documentId],
          (prev) =>
            prev
              ? {
                  ...prev,
                  status: patch.status as Document["status"],
                }
              : prev
        );
      }
    };

    const handleSseEvent = (eventType: string, rawData: string) => {
      let data: Record<string, unknown> = {};
      try {
        data = JSON.parse(rawData) as Record<string, unknown>;
      } catch {
        return;
      }

      if (eventType === "status") {
        applyStatusPatch({
          status: typeof data.status === "string" ? data.status : undefined,
          job_status: typeof data.job_status === "string" ? data.job_status : undefined,
          stage: typeof data.stage === "string" ? data.stage : undefined,
          total_clauses:
            typeof data.total_clauses === "number" ? data.total_clauses : undefined,
          analyzed_clauses:
            typeof data.analyzed_clauses === "number" ? data.analyzed_clauses : undefined,
        });
      } else if (eventType === "batch_completed") {
        const committed =
          typeof data.total_committed === "number" ? data.total_committed : undefined;
        const total =
          typeof data.total_clauses === "number" ? data.total_clauses : undefined;
        applyStatusPatch({
          status: "analyzing",
          job_status: "running",
          stage: "analyzing",
          analyzed_clauses: committed,
          total_clauses: total,
        });
        queryClient.invalidateQueries({ queryKey: ["analysis", documentId, "clauses"] });
      } else if (eventType === "score_computed") {
        setIsProvisional(Boolean(data.is_provisional ?? true));
        applyStatusPatch({
          status: "analyzing",
          job_status: "running",
          stage: "summarizing",
        });
        queryClient.invalidateQueries({ queryKey: ["analysis", documentId, "summary"] });
        queryClient.invalidateQueries({ queryKey: ["documents", documentId] });
      } else if (eventType === "completed") {
        setIsProvisional(false);
        applyStatusPatch({
          status: "completed",
          job_status: "completed",
          stage: "completed",
          progress: 1,
        });
        queryClient.invalidateQueries({ queryKey: ["documents", documentId] });
        queryClient.invalidateQueries({ queryKey: ["documents"] });
        queryClient.invalidateQueries({ queryKey: ["analysis", documentId, "summary"] });
        queryClient.invalidateQueries({ queryKey: ["analysis", documentId, "clauses"] });
        queryClient.invalidateQueries({ queryKey: ["analysis", documentId, "status"] });
        stopped = true;
        controller.abort("stream_completed");
      } else if (eventType === "waiting_for_quota") {
        setIsProvisional(false);
        applyStatusPatch({
          status: "waiting for quota",
          job_status: "waiting_for_quota",
          stage: "waiting_for_quota",
          message: typeof data.message === "string" ? data.message : undefined,
        });
        queryClient.invalidateQueries({ queryKey: ["documents", documentId] });
        queryClient.invalidateQueries({ queryKey: ["analysis", documentId, "clauses"] });
        queryClient.invalidateQueries({ queryKey: ["analysis", documentId, "status"] });
      } else if (eventType === "cancelling") {
        applyStatusPatch({
          status: "cancelling",
          job_status: "cancelling",
          stage: "cancelling",
        });
      } else if (eventType === "cancelled") {
        applyStatusPatch({
          status: "cancelled",
          job_status: "cancelled",
          stage: "cancelled",
        });
        queryClient.invalidateQueries({ queryKey: ["documents", documentId] });
        queryClient.invalidateQueries({ queryKey: ["documents"] });
        stopped = true;
        controller.abort("stream_cancelled");
      } else if (eventType === "failed") {
        applyStatusPatch({
          status: "failed",
          job_status: "failed",
          stage: "failed",
          message: typeof data.message === "string" ? data.message : undefined,
        });
        queryClient.invalidateQueries({ queryKey: ["documents", documentId] });
        queryClient.invalidateQueries({ queryKey: ["documents"] });
        stopped = true;
        controller.abort("stream_failed");
      }
    };

    const connect = async () => {
      const token =
        typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      if (!token) return;

      try {
        const res = await fetch(`${API_BASE_URL}/documents/${documentId}/events`, {
          method: "GET",
          headers: {
            Accept: "text/event-stream",
            Authorization: `Bearer ${token}`,
          },
          signal: controller.signal,
        });
        if (!res.ok || !res.body) return;

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!stopped && !controller.signal.aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const blocks = buffer.split(/\r?\n\r?\n/);
          buffer = blocks.pop() ?? "";

          for (const block of blocks) {
            if (!block.trim() || block.startsWith(":")) continue;
            let eventName = "message";
            const dataLines: string[] = [];
            for (const line of block.split(/\r?\n/)) {
              if (line.startsWith("event:")) {
                eventName = line.slice(6).trim();
              } else if (line.startsWith("data:")) {
                dataLines.push(line.slice(5).trim());
              }
            }
            if (dataLines.length > 0) {
              handleSseEvent(eventName, dataLines.join("\n"));
            }
          }
        }
      } catch {
        // Expected on AbortController cancellation or navigation
      }
    };

    void connect();

    return () => {
      stopped = true;
      unregister();
      controller.abort("unmount");
    };
  }, [documentId, enabled, queryClient]);

  return { isProvisional, setIsProvisional };
}

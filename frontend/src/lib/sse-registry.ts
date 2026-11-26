/**
 * Global registry of active SSE AbortControllers keyed by documentId.
 *
 * Allows delete, logout, and account deletion handlers to terminate open
 * Event/SSE streams immediately so zero further progress events arrive.
 */

const activeStreams = new Map<string, Set<AbortController>>();

export function registerDocumentStream(documentId: string, controller: AbortController): () => void {
  let set = activeStreams.get(documentId);
  if (!set) {
    set = new Set();
    activeStreams.set(documentId, set);
  }
  set.add(controller);

  return () => {
    const current = activeStreams.get(documentId);
    if (current) {
      current.delete(controller);
      if (current.size === 0) {
        activeStreams.delete(documentId);
      }
    }
  };
}

export function closeDocumentStream(documentId: string): void {
  const controllers = activeStreams.get(documentId);
  if (!controllers) return;
  for (const controller of controllers) {
    try {
      controller.abort("document_deleted_or_cancelled");
    } catch {
      // Ignore abort errors on already-closed controllers
    }
  }
  activeStreams.delete(documentId);
}

export function closeAllDocumentStreams(): void {
  for (const documentId of Array.from(activeStreams.keys())) {
    closeDocumentStream(documentId);
  }
}

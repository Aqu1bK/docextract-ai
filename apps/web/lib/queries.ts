// docextract-ai/apps/web/lib/queries.ts

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { ApiError, DocumentSummary, Paginated } from './api';
import { api } from './api';

/**
 * TanStack Query hooks — the app's only data-layer entry points.
 *
 * Queries (`useDocuments`) read server state: one queryKey per parameter
 * set, so page 2 and page 3 are separately cached and "back" is instant.
 * Mutations (`useUploadDocument`) write server state and then invalidate
 * the affected queryKey, which refetches the documents list in the
 * background — the list never shows an upload the backend has not
 * confirmed. TanStack v5 signature: object arguments only
 * (useQuery({ queryKey, queryFn }), useMutation({ mutationFn, ... })).
 *
 * Phase 9C adds the review surface's hooks: document detail, fields,
 * audit logs, exports, the polling extraction status (refetchInterval
 * that stops on terminal states), the field/document mutations, the
 * export creation, and the source-PDF blob URL. Field and document
 * mutations invalidate both their own key and the document's, so the
 * status badge and the approval panel's blockers update in the same
 * sweep as the row the reviewer acted on.
 */

/**
 * Documents list query, keyed by page so each page caches separately.
 * `keepPreviousData` dims the stale page while the next one loads instead
 * of flashing the skeleton.
 *
 * The error generic is pinned to `ApiError` because `fetchWithAuth` in
 * lib/api.ts throws ApiError on any non-2xx response — callers downstream
 * (the documents table's error panel) branch on `error.code`.
 */
export function useDocuments(params: { page?: number; pageSize?: number } = {}) {
  const page = params.page ?? 1;
  const pageSize = params.pageSize ?? 20;
  return useQuery<Paginated<DocumentSummary>, ApiError>({
    queryKey: ['documents', page, pageSize],
    queryFn: () => api.getDocuments({ page, pageSize }),
    placeholderData: keepPreviousData,
  });
}

/**
 * The full two-step upload flow as one mutation.
 *
 * Step 1 mints the signed URL (API), step 2 PUTs the bytes to object
 * storage (never through the API), step 3 confirms (API). The three steps
 * are one mutation because they are one business action — a document —
 * and the caller (the upload page) should be able to treat "upload a
 * File" as a single async unit with one success and one failure path.
 *
 * `onSuccess` invalidates the documents key: every cached page of the
 * list is marked stale, active lists refetch, and the table shows the
 * new row without a manual refresh.
 */
export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ file }: { file: File }) => {
      // Step 1: request the signed upload URL from the API.
      const upload = await api.requestUploadUrl({
        file_name: file.name,
        content_type: file.type,
        size_bytes: file.size,
      });

      // Step 2: upload the bytes straight to storage with the signed URL.
      // The Content-Type header travels with the PUT so the stored object
      // matches what the API's confirm step will re-verify.
      const put = await fetch(upload.upload_url, {
        method: upload.upload_method,
        headers: { ...upload.upload_headers, 'Content-Type': file.type },
        body: file,
      });
      if (!put.ok) {
        throw new Error(`Storage upload failed with status ${put.status}`);
      }

      // Step 3: confirm with the API, which verifies the object and
      // writes the documents row.
      const confirmed = await api.confirmUpload({
        document_id: upload.document_id,
        storage_path: upload.storage_path,
        file_name: file.name,
        content_type: file.type,
        size_bytes: file.size,
      });

      // Return the DocumentSummary shape for the success toast.
      return {
        id: confirmed.document.id,
        filename: confirmed.document.file_name,
        size_bytes: confirmed.document.size_bytes,
        created_at: confirmed.document.created_at,
      };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

// ----------------------------------------------------------------------
// Phase 9C — the review surface's queries and mutations.
// ----------------------------------------------------------------------

/** One document's metadata, keyed by id. */
export function useDocumentDetail(documentId: string) {
  return useQuery({
    queryKey: ['document', documentId],
    queryFn: () => api.getDocument(documentId),
  });
}

/** Every extracted field of one document, keyed by document. */
export function useDocumentFields(documentId: string) {
  return useQuery({
    queryKey: ['document-fields', documentId],
    queryFn: () => api.getDocumentFields(documentId),
  });
}

/** One document's audit trail, newest first. */
export function useAuditLogs(documentId: string) {
  return useQuery({
    queryKey: ['audit-logs', documentId],
    queryFn: () => api.getAuditLogs(documentId),
  });
}

/** One document's past exports, newest first. */
export function useExports(documentId: string) {
  return useQuery({
    queryKey: ['exports', documentId],
    queryFn: () => api.getExports(documentId),
  });
}

/**
 * The extraction status poll: document status + latest job.
 *
 * refetchInterval as a callback is TanStack v5's terminal-state pattern:
 * the query inspects its own latest data and returns false to stop
 * polling once the document reaches a status the pipeline never leaves.
 * While mid-pipeline it returns 3000 — a page left open refreshes every
 * three seconds without a websocket and stops the moment there is
 * nothing left to wait for.
 */
export function useExtractionStatus(documentId: string) {
  return useQuery({
    queryKey: ['extraction-status', documentId],
    queryFn: () => api.getExtractionStatus(documentId),
    refetchInterval: (query) => {
      const status = query.state.data?.document_status;
      return ['approved', 'rejected', 'failed', 'archived'].includes(status ?? '') ? false : 3000;
    },
  });
}

/**
 * The source PDF as a blob URL for the review screen's PDF pane.
 *
 * The API download requires the Authorization header (a plain link
 * cannot carry it), so the query fetches the bytes with the session
 * token and object-URLs them — same-origin, which is exactly what
 * pdf.js's worker requires. The URL is revoked when the query's owner
 * unmounts (garbage collection handles the blob's backing data once
 * unreferenced; object URLs created per query instance are bounded by
 * the document detail screen's lifetime).
 */
export function useDocumentDownloadUrl(documentId: string) {
  return useQuery({
    queryKey: ['document-download', documentId],
    queryFn: () => api.getDocumentDownloadUrl(documentId),
    // A fetched blob never changes for one document id: never refetch.
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: Number.POSITIVE_INFINITY,
  });
}

/**
 * Correct one field: the reviewer's replacement value (and optional
 * reason) travel to PATCH; the machine original is preserved server-side.
 */
export function useCorrectField(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fieldId, value, reason }: { fieldId: string; value: string; reason?: string }) =>
      api.correctField(fieldId, { value, reason }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['document-fields', documentId] });
      void queryClient.invalidateQueries({ queryKey: ['document', documentId] });
      void queryClient.invalidateQueries({ queryKey: ['audit-logs', documentId] });
    },
  });
}

/** Accept one field's machine value unchanged. */
export function useAcceptField(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fieldId }: { fieldId: string }) => api.acceptField(fieldId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['document-fields', documentId] });
      void queryClient.invalidateQueries({ queryKey: ['document', documentId] });
      void queryClient.invalidateQueries({ queryKey: ['audit-logs', documentId] });
    },
  });
}

/** Reject one field: clear its value, keep the machine original. */
export function useRejectField(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fieldId, reason }: { fieldId: string; reason?: string }) =>
      api.rejectField(fieldId, { reason }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['document-fields', documentId] });
      void queryClient.invalidateQueries({ queryKey: ['document', documentId] });
      void queryClient.invalidateQueries({ queryKey: ['audit-logs', documentId] });
    },
  });
}

/** Approve the document (the backend enforces the blocking conditions). */
export function useApproveDocument(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.approveDocument(documentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['document', documentId] });
      void queryClient.invalidateQueries({ queryKey: ['documents'] });
      void queryClient.invalidateQueries({ queryKey: ['audit-logs', documentId] });
    },
  });
}

/** Reject the document with an optional reason for the trail. */
export function useRejectDocument(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reason }: { reason?: string }) => api.rejectDocument(documentId, { reason }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['document', documentId] });
      void queryClient.invalidateQueries({ queryKey: ['documents'] });
      void queryClient.invalidateQueries({ queryKey: ['audit-logs', documentId] });
    },
  });
}

/** Generate one export (JSON or CSV) and invalidate the document's list. */
export function useCreateExport(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ format }: { format: 'json' | 'csv' }) =>
      api.createExport(documentId, { format }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['exports', documentId] });
      void queryClient.invalidateQueries({ queryKey: ['audit-logs', documentId] });
    },
  });
}
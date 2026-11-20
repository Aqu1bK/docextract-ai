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
 * confirmed. TanStack v5 signature: object arguments only.
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
 * and the caller treats "upload a File" as a single async unit.
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
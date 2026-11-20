// docextract-ai/apps/web/lib/api.ts

import { env } from './env';
import { createClient } from './supabase-browser';

/**
 * Typed client for the FastAPI backend (`/api/v1`).
 *
 * One fetch wrapper owns everything the backend's contract needs: the
 * Authorization header (from the Supabase session), JSON content type,
 * and the error envelope. Every call goes through it, so "attach the
 * token, unwrap the envelope" is written once instead of per screen.
 *
 * The session comes from the browser client's cookie jar: getSession()
 * reads (and, if needed, refreshes) the session the @supabase/ssr factory
 * keeps in cookies, so the token is fresh at call time. Requests without
 * a session are sent unauthenticated — the backend's 401 is the honest
 * answer, and pages treat it as data.
 */

/** The backend's error envelope: { error: { code, message, details } }. */
export interface ApiErrorEnvelope {
  error: { code: string; message: string; details: unknown };
}

/**
 * Error type carrying the backend's code + message.
 *
 * Thrown for any non-2xx response so callers can branch on `code`
 * (e.g. VALIDATION_ERROR vs STORAGE_VERIFICATION_FAILED) without
 * parsing strings.
 */
export class ApiError extends Error {
  /** Backend error code, e.g. UNAUTHORIZED or VALIDATION_ERROR. */
  readonly code: string;
  /** Machine-readable details from the envelope, when present. */
  readonly details: unknown;
  /** HTTP status of the failed response. */
  readonly status: number;

  constructor(code: string, message: string, status: number, details: unknown) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

/** One page of documents, as GET /documents returns (raw backend shape). */
export interface DocumentRecord {
  id: string;
  file_name: string;
  content_type: string;
  status: string;
  page_count: number | null;
  sha256: string;
  size_bytes: number;
  created_at: string;
}

/** GET /documents response body. */
export interface DocumentsListResponse {
  documents: DocumentRecord[];
  total: number;
}

/** POST /documents/upload-url response body. */
export interface UploadUrlResponse {
  document_id: string;
  upload_url: string;
  upload_method: string;
  upload_headers: Record<string, string>;
  storage_path: string;
  max_size_bytes: number;
  expires_in_seconds: number;
}

/** POST /documents (confirm) response body. */
export interface ConfirmUploadResponse {
  document: DocumentRecord;
  duplicate_of_document_id: string | null;
}

/** Pipeline status values matching the backend's DocumentStatus enum. */
export type DocumentStatus =
  | 'uploaded'
  | 'queued'
  | 'processing'
  | 'needs_review'
  | 'ready_for_review'
  | 'approved'
  | 'rejected'
  | 'failed'
  | 'archived';

/** One document summary (9B naming — camelCase fields). */
export type DocumentSummary = {
  id: string;
  filename: string;
  content_type: string;
  status: DocumentStatus;
  page_count: number | null;
  sha256: string;
  size_bytes: number;
  created_at: string;
};

/** Paginated list wrapper (9B contract). */
export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

/** Transform backend's DocumentRecord → DocumentSummary. */
function toSummary(record: DocumentRecord): DocumentSummary {
  return {
    id: record.id,
    filename: record.file_name,
    content_type: record.content_type,
    status: record.status as DocumentStatus,
    page_count: record.page_count,
    sha256: record.sha256,
    size_bytes: record.size_bytes,
    created_at: record.created_at,
  };
}

/** One extracted field (9C). */
export interface FieldRecord {
  id: string;
  field_key: string;
  field_label: string;
  value_text: string | null;
  confidence: number;
  source: string;
  page_number: number | null;
  review_status: string;
  original_value_text: string | null;
  is_required: boolean;
}

/** One audit log row (9C). */
export interface AuditLogRecord {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  actor_user_id: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

/** One export row (9C). */
export interface ExportRecord {
  id: string;
  format: 'json' | 'csv';
  status: 'pending' | 'completed' | 'failed';
  row_count: number | null;
  expires_at: string | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

/** Extraction status response (9C). */
export interface ExtractionStatusResponse {
  document_status: string;
  latest_job: {
    id: string;
    status: string;
    attempts: number;
    max_attempts: number;
    error_code: string | null;
    error_message: string | null;
    created_at: string;
    completed_at: string | null;
  } | null;
}

/**
 * Fetch a backend path with the session token, returning parsed JSON.
 *
 * `path` is the part after the /api/v1 base ("/documents", not the full
 * URL). Non-2xx responses are parsed as the error envelope and raised as
 * ApiError; network failures propagate as native TypeError (fetch's
 * behavior), which callers surface as a generic toast.
 */
async function fetchWithAuth<T>(path: string, init: RequestInit = {}): Promise<T> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(init.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    ...(session !== null ? { Authorization: `Bearer ${session.access_token}` } : {}),
    ...(init.headers as Record<string, string> | undefined),
  };

  const response = await fetch(`${env.apiBaseUrl}${path}`, { ...init, headers });

  if (!response.ok) {
    let code = 'HTTP_ERROR';
    let message = `Request failed with status ${response.status}`;
    let details: unknown = null;

    try {
      const envelope = (await response.json()) as ApiErrorEnvelope;
      code = envelope.error?.code ?? code;
      message = envelope.error?.message ?? message;
      details = envelope.error?.details ?? null;
    } catch {
      // Non-JSON body (proxy error, empty 500): keep the status-based defaults.
    }

    throw new ApiError(code, message, response.status, details);
  }

  // 204-style empty bodies (none today, but future DELETEs) parse as null.
  const text = await response.text();
  return (text === '' ? null : JSON.parse(text)) as T;
}

/**
 * The backend surface Phases 9B and 9C need: list, detail, the
 * two-step upload flow, review/audit/export reads and mutations, the
 * job status poll, and the source-PDF read URL — one place to extend,
 * not many.
 */
export const api = {
  /** GET /documents — paginated, returns DocumentSummary (9B contract). */
  getDocuments(
    params: { page?: number; pageSize?: number } = {},
  ): Promise<Paginated<DocumentSummary>> {
    const page = params.page ?? 1;
    const pageSize = params.pageSize ?? 20;
    const skip = (page - 1) * pageSize;
    const query = new URLSearchParams({
      skip: String(skip),
      limit: String(pageSize),
    });
    return fetchWithAuth<DocumentsListResponse>(`/documents?${query.toString()}`).then((res) => ({
      items: res.documents.map(toSummary),
      total: res.total,
      page,
      page_size: pageSize,
      total_pages: Math.max(1, Math.ceil(res.total / pageSize)),
    }));
  },

  /** GET /documents/{id} — one document's metadata (raw backend shape). */
  getDocument(id: string): Promise<DocumentRecord> {
    return fetchWithAuth<DocumentRecord>(`/documents/${id}`);
  },

  /** GET /review/documents/{id}/fields — all fields with review status (9C). */
  getDocumentFields(documentId: string): Promise<FieldRecord[]> {
    return fetchWithAuth<FieldRecord[]>(`/review/documents/${documentId}/fields`);
  },

  /** PATCH /review/fields/{id} — correct one field's value (9C). */
  correctField(fieldId: string, data: { value: string; reason?: string }): Promise<FieldRecord> {
    return fetchWithAuth<FieldRecord>(`/review/fields/${fieldId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /** POST /review/fields/{id}/accept (9C). */
  acceptField(fieldId: string): Promise<FieldRecord> {
    return fetchWithAuth<FieldRecord>(`/review/fields/${fieldId}/accept`, { method: 'POST' });
  },

  /** POST /review/fields/{id}/reject (9C). */
  rejectField(fieldId: string, data: { reason?: string }): Promise<FieldRecord> {
    return fetchWithAuth<FieldRecord>(`/review/fields/${fieldId}/reject`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /** POST /review/documents/{id}/approve (9C). */
  approveDocument(documentId: string): Promise<DocumentRecord> {
    return fetchWithAuth<DocumentRecord>(`/review/documents/${documentId}/approve`, {
      method: 'POST',
    });
  },

  /** POST /review/documents/{id}/reject (9C). */
  rejectDocument(documentId: string, data: { reason?: string }): Promise<DocumentRecord> {
    return fetchWithAuth<DocumentRecord>(`/review/documents/${documentId}/reject`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /** GET /audit/documents/{id}/logs (9C). */
  getAuditLogs(documentId: string): Promise<AuditLogRecord[]> {
    return fetchWithAuth<AuditLogRecord[]>(`/audit/documents/${documentId}/logs`);
  },

  /** GET /exports/documents/{id}/exports (9C). */
  getExports(documentId: string): Promise<ExportRecord[]> {
    return fetchWithAuth<ExportRecord[]>(`/exports/documents/${documentId}/exports`);
  },

  /** POST /exports/documents/{id}/export (9C). */
  createExport(documentId: string, data: { format: 'json' | 'csv' }): Promise<ExportRecord> {
    return fetchWithAuth<ExportRecord>(`/exports/documents/${documentId}/export`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /** GET /extraction/documents/{id}/extraction-status (9C). */
  getExtractionStatus(documentId: string): Promise<ExtractionStatusResponse> {
    return fetchWithAuth<ExtractionStatusResponse>(
      `/extraction/documents/${documentId}/extraction-status`,
    );
  },

  /** POST /documents/upload-url (9B). */
  requestUploadUrl(data: {
    file_name: string;
    content_type: string;
    size_bytes: number;
  }): Promise<UploadUrlResponse> {
    return fetchWithAuth<UploadUrlResponse>('/documents/upload-url', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /** POST /documents — confirm upload (9B). */
  confirmUpload(data: {
    document_id: string;
    storage_path: string;
    file_name: string;
    content_type: string;
    size_bytes: number;
  }): Promise<ConfirmUploadResponse> {
    return fetchWithAuth<ConfirmUploadResponse>('/documents', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * GET /documents/{id}/download — a short-lived read URL for the source PDF (9C).
   *
   * The endpoint responds with the object's bytes; calling it with
   * fetch and reading the blob URL gives the viewer a same-origin URL
   * pdf.js can load, while the Authorization header (which a plain
   * <a href> cannot carry) authenticates the read.
   */
  async getDocumentDownloadUrl(id: string): Promise<string> {
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    const headers: Record<string, string> = {
      Accept: 'application/pdf',
      ...(session !== null ? { Authorization: `Bearer ${session.access_token}` } : {}),
    };

    const response = await fetch(`${env.apiBaseUrl}/documents/${id}/download`, { headers });
    if (!response.ok) {
      throw new ApiError(
        'DOWNLOAD_FAILED',
        'The document could not be fetched.',
        response.status,
        null,
      );
    }

    const blob = await response.blob();
    return URL.createObjectURL(blob);
  },
};
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

/** One page of documents, as GET /documents returns. */
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

/** One document summary (Chunk 4 naming). */
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

/** Paginated list wrapper (Chunk 4 contract). */
export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

/** Transform the backend's DocumentRecord → DocumentSummary (snake_case rename). */
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
 * The backend surface Phase 9B needs: list, detail, and the two-step
 * upload flow. 9C extends this object with review/export/audit calls —
 * one place to extend, not many.
 */
export const api = {
  /** GET /documents — one page of the org's documents, newest first. */
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
    return fetchWithAuth<DocumentsListResponse>(`/documents?${query.toString()}`).then(
      (res) => ({
        items: res.documents.map(toSummary),
        total: res.total,
        page,
        page_size: pageSize,
        total_pages: Math.max(1, Math.ceil(res.total / pageSize)),
      }),
    );
  },

  /** GET /documents/{id} — one document's metadata. */
  getDocument(id: string): Promise<DocumentRecord> {
    return fetchWithAuth<DocumentRecord>(`/documents/${id}`);
  },

  /** POST /documents/upload-url — step 1 of the upload flow: mint the signed URL. */
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

  /** POST /documents — step 2: confirm the object landed in storage. */
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
};
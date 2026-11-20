'use client';

import { Download } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { env } from '@/lib/env';
import type { ExportRecord } from '@/lib/api';

/**
 * ExportRow — one past export with its download link.
 *
 * The row is metadata (format, status, rows, when it completes, when
 * retention expires it) plus, for COMPLETED exports, the download
 * action. The download is a plain link to the API's download endpoint —
 * the browser follows it with the session cookie already present, and
 * the endpoint responds with Content-Disposition: attachment, which is
 * what makes it a save dialog rather than a page navigation. Failed
 * exports show their error message instead of a link, because there
 * are no bytes to fetch.
 */
export interface ExportRowProps {
  /** The export row to render. */
  exportRecord: ExportRecord;
  /** The document the export belongs to (its id builds the link). */
  documentId: string;
}

/** ISO timestamp → "Nov 20, 14:32" — the precision a retention list needs. */
function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function ExportRow({ exportRecord, documentId }: ExportRowProps) {
  const downloadHref = `${env.apiBaseUrl}/documents/${documentId}/exports/${exportRecord.id}/download`;

  return (
    <li className="flex items-center justify-between gap-4 border-b border-rule px-3 py-2.5 last:border-b-0">
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-ink">{exportRecord.format}</span>
        <Badge
          variant={exportRecord.status === 'completed' ? 'status-accepted' : 'status-rejected'}
        >
          {exportRecord.status}
        </Badge>
        <span className="text-xs text-ink-muted">
          {exportRecord.row_count !== null ? `${exportRecord.row_count} rows` : '—'}
        </span>
        <span className="text-xs text-ink-muted">
          {exportRecord.completed_at !== null
            ? formatTimestamp(exportRecord.completed_at)
            : 'in progress'}
        </span>
        {exportRecord.expires_at !== null ? (
          <span className="text-xs text-ink-muted" title="Retention expiry">
            expires {formatTimestamp(exportRecord.expires_at)}
          </span>
        ) : null}
      </div>

      <div className="shrink-0">
        {exportRecord.status === 'completed' ? (
          <Button variant="outline" size="sm" asChild>
            <a href={downloadHref} download>
              <Download className="size-3.5" aria-hidden />
              Download
            </a>
          </Button>
        ) : exportRecord.status === 'failed' && exportRecord.error_message !== null ? (
          <span
            className="max-w-40 truncate text-xs text-confidence-low"
            title={exportRecord.error_message}
          >
            {exportRecord.error_message}
          </span>
        ) : (
          <span className="text-xs text-ink-muted">pending</span>
        )}
      </div>
    </li>
  );
}
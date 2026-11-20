// docextract-ai/apps/web/components/documents/document-row.tsx

import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { TableRow } from '@/components/ui/table';
import type { DocumentSummary } from '@/lib/api';

/**
 * Status badge for a document row.
 *
 * The nine DocumentStatus values map onto exactly two visual tones for
 * this table: "in the machine" (uploaded/queued/processing — ink-muted,
 * the pipeline is working, no human attention needed) and "waiting for
 * a human" (needs_review/ready_for_review — the accent blue that the
 * sidebar's active edge also uses, because this is the queue the
 * product exists to serve). Terminal states use their natural colors:
 * approved reads green, rejected reads red, failed reads red, archived
 * returns to muted.
 */

/** The two visual tones this table uses: pipeline-quiet vs review-pending. */
type RowVariant = 'outline' | 'accent';

const STATUS_BADGE: Record<string, { label: string; variant: RowVariant }> = {
  uploaded: { label: 'Uploaded', variant: 'outline' },
  queued: { label: 'Queued', variant: 'outline' },
  processing: { label: 'Processing', variant: 'outline' },
  needs_review: { label: 'Needs review', variant: 'accent' },
  ready_for_review: { label: 'Ready for review', variant: 'accent' },
  approved: { label: 'Approved', variant: 'outline' },
  rejected: { label: 'Rejected', variant: 'outline' },
  failed: { label: 'Failed', variant: 'outline' },
  archived: { label: 'Archived', variant: 'outline' },
};

/** Human-readable byte size: 1536 → "1.5 KB", 5 MB stays "5.0 MB". */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** ISO timestamp → "Nov 19, 14:26" — enough precision for a review queue. */
export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * One row of the documents table.
 *
 * File name is the row's identity (mono font — a file name is a machine
 * string, not prose); size and pages are right-aligned numerals; the
 * status badge closes the row. The file name links to the document's
 * review screen (9C): the register is the review queue, so opening a
 * row's document is the row's one action, and the name is the natural
 * anchor (full-row overlays are link-shaped but focus-shaped wrong).
 */
export function DocumentRow({ document }: { document: DocumentSummary }) {
  const status = STATUS_BADGE[document.status] ?? { label: document.status, variant: 'outline' };

  return (
    <TableRow className="border-b border-rule transition-colors hover:bg-paper-muted">
      <td className="max-w-[24rem] truncate px-3 py-2.5 align-middle font-mono text-xs text-ink">
        <Link
          href={`/documents/${document.id}`}
          className="underline-offset-4 hover:underline"
          title="Open review screen"
        >
          {document.filename}
        </Link>
      </td>
      <td className="px-3 py-2.5 align-middle text-sm text-ink-muted">
        {document.created_at ? formatTimestamp(document.created_at) : '—'}
      </td>
      <td className="px-3 py-2.5 align-middle text-right text-sm text-ink-muted">
        {document.page_count ?? '—'}
      </td>
      <td className="px-3 py-2.5 align-middle text-right text-sm text-ink-muted">
        {formatBytes(document.size_bytes)}
      </td>
      <td className="px-3 py-2.5 align-middle">
        {status.variant === 'accent' ? (
          <span className="border border-accent/30 bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
            {status.label}
          </span>
        ) : (
          <Badge variant="outline">{status.label}</Badge>
        )}
      </td>
    </TableRow>
  );
}
import { Badge } from '@/components/ui/badge'
import { TableCell, TableRow } from '@/components/ui/table'
import { cn } from '@/lib/utils'
import type { DocumentStatus, DocumentSummary } from '@/lib/api'

/**
 * DocumentRow — one register line, plus the register's shared helpers.
 *
 * Provenance typography rules for the row: filenames, sizes, and
 * timestamps are machine artifacts (JetBrains Mono); status labels are
 * machine state and also mono, but carried by an outline badge with a
 * square state dot — zero radius, per the design language.
 */

interface StatusMeta {
  /** Human-facing label, rendered uppercase by the badge's CSS. */
  label: string
  /** Square dot fill. Colors come from the 9A status token scale. */
  dot: string
}

/**
 * Pipeline status -> semantic status color. Two in-flight states share
 * status-info; review states map to warning / ok / error. The API owns
 * the raw enum (lib/api.ts DocumentStatus); this mapping owns the prose
 * and the ink.
 */
const STATUS_META: Record<DocumentStatus, StatusMeta> = {
  uploaded: { label: 'Uploaded', dot: 'bg-rule' },
  queued: { label: 'Queued', dot: 'bg-status-info' },
  processing: { label: 'Processing', dot: 'bg-status-info' },
  needs_review: { label: 'Needs review', dot: 'bg-status-warning' },
  ready_for_review: { label: 'Ready for review', dot: 'bg-status-warning' },
  approved: { label: 'Approved', dot: 'bg-status-ok' },
  rejected: { label: 'Rejected', dot: 'bg-status-error' },
  failed: { label: 'Failed', dot: 'bg-status-error' },
  archived: { label: 'Archived', dot: 'bg-rule' },
}

/**
 * Status lookup with a forward-compatible fallback: an unrecognized
 * status renders with a neutral rule-colored dot and the machine's own
 * spelling as the label — the register shows exactly what the API said
 * rather than guessing.
 */
export function statusMeta(status: string): StatusMeta {
  return STATUS_META[status as DocumentStatus] ?? { label: status, dot: 'bg-rule' }
}

/**
 * formatBytes — byte count to the human scale (B / KB / MB / GB).
 *
 * Pure and deterministic so it can be asserted in tests: no locale
 * machinery, one fractional digit for everything above bytes.
 */
export function formatBytes(bytes: number, fractionDigits = 1): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return '0 B'
  }

  const units = ['B', 'KB', 'MB', 'GB'] as const
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / 1024 ** exponent

  return `${value.toFixed(exponent === 0 ? 0 : fractionDigits)} ${units[exponent]}`
}

/**
 * formatTimestamp — ISO 8601 string to the machine register's timestamp:
 * `YYYY-MM-DD HH:mm`, in the viewer's local timezone.
 *
 * Values that fail to parse are returned verbatim so a malformed payload
 * stays visible in review instead of silently becoming "Invalid Date".
 */
export function formatTimestamp(value: string): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  const pad = (part: number) => String(part).padStart(2, '0')

  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

interface DocumentRowProps {
  document: DocumentSummary
}

/**
 * A row is not yet a link — document detail navigation lands with the
 * review phase, which owns the /documents/[id] route.
 */
export function DocumentRow({ document }: DocumentRowProps) {
  const meta = statusMeta(document.status)

  return (
    <TableRow>
      <TableCell className="max-w-[28ch] sm:max-w-[32rem]">
        <span className="block truncate font-mono text-sm text-ink" title={document.filename}>
          {document.filename}
        </span>
      </TableCell>

      <TableCell className="text-right font-mono text-sm text-ink/70">
        {formatBytes(document.size_bytes)}
      </TableCell>

      <TableCell>
        <Badge
          variant="outline"
          className="gap-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-ink/70"
        >
          {/* Square state dot — zero-radius system. */}
          <span aria-hidden="true" className={cn('h-1.5 w-1.5 shrink-0', meta.dot)} />
          {meta.label}
        </Badge>
      </TableCell>

      <TableCell className="whitespace-nowrap font-mono text-[13px] text-ink/60">
        {formatTimestamp(document.created_at)}
      </TableCell>
    </TableRow>
  )
}
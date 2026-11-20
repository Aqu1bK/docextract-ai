'use client'

import Link from 'next/link'
import type { UseQueryResult } from '@tanstack/react-query'

import { DocumentRow } from '@/components/documents/document-row'
import { Button, buttonVariants } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableCaption,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { ApiError } from '@/lib/api'
import type { DocumentSummary, Paginated } from '@/lib/api'

/** Placeholder rows while the first page loads. */
const SKELETON_ROW_COUNT = 6

interface DocumentsTableProps {
  /** The live query owned by DocumentsView. */
  query: UseQueryResult<Paginated<DocumentSummary>, ApiError>
  /** Authoritative page from the view (query data may be stale mid-flight). */
  page: number
  onPageChange: (page: number) => void
}

/**
 * DocumentsTable — the register, with all four states rendered explicitly:
 *
 * 1. isPending   — no cached data at all (first load) -> skeleton rows.
 * 2. isError     — load failed -> message + retry.
 * 3. empty       — loaded, zero documents -> pointer to intake.
 * 4. data        — the register + pagination controls.
 *
 * Page changes are NOT the skeleton case: `keepPreviousData` (configured
 * on `useDocuments` in lib/queries.ts) keeps the previous page mounted
 * while the next one loads, and `isPlaceholderData` dims it instead. The
 * skeleton is reserved for the true cold start.
 */
export function DocumentsTable({ query, page, onPageChange }: DocumentsTableProps) {
  if (query.isPending) {
    return <SkeletonTable />
  }

  if (query.isError) {
    return <ErrorPanel error={query.error} onRetry={() => query.refetch()} />
  }

  const { items, total, total_pages } = query.data

  if (items.length === 0) {
    return <EmptyState />
  }

  return (
    <div className="flex flex-col gap-4">
      <div
        aria-busy={query.isFetching}
        className={cn(
          'border border-rule bg-paper',
          // Stale page while the next one loads: an instant opacity step,
          // no animation. Honest signal that this data is being replaced.
          query.isPlaceholderData && 'opacity-60'
        )}
      >
        <Table>
          <TableCaption className="sr-only">Documents, newest first.</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Filename</TableHead>
              {/* Numeric column — right-aligned; twMerge resolves the
                  base `text-left` in the primitive. */}
              <TableHead className="text-right">Size</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Uploaded</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((document) => (
              <DocumentRow key={document.id} document={document} />
            ))}
          </TableBody>
        </Table>
      </div>

      <Pagination
        page={page}
        total={total}
        totalPages={total_pages}
        isFetching={query.isFetching}
        onPageChange={onPageChange}
      />
    </div>
  )
}

/**
 * State 1 — skeleton. Static ink bars, deliberately NOT pulsing: the
 * design language has no animation, and a static skeleton communicates
 * "shaping up" just as well. Screen readers get a polite status instead.
 */
function SkeletonTable() {
  return (
    <div className="flex flex-col gap-4">
      <span role="status" className="sr-only">
        Loading documents…
      </span>
      <div className="border border-rule bg-paper">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Filename</TableHead>
              <TableHead className="text-right">Size</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Uploaded</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: SKELETON_ROW_COUNT }, (_, index) => (
              <TableRow key={index}>
                <TableCell>
                  <div className={cn('h-3 bg-ink/[0.08]', index % 3 === 2 ? 'w-56' : 'w-72')} />
                </TableCell>
                <TableCell>
                  <div className="ml-auto h-3 w-14 bg-ink/[0.08]" />
                </TableCell>
                <TableCell>
                  <div className="h-3 w-24 bg-ink/[0.08]" />
                </TableCell>
                <TableCell>
                  <div className="h-3 w-32 bg-ink/[0.08]" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

/** Server detail when we have it; a plain-language line when we do not. */
function describeLoadFailure(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  return 'Could not reach the API. Check your connection and try again.'
}

/**
 * State 2 — error. The retry refetches the same page; pagination state
 * (owned by the view) is untouched, so a retry after paging resumes
 * exactly where the user was.
 */
function ErrorPanel({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 border border-rule bg-paper px-6 py-16 text-center"
    >
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/50">error</p>
      <p className="max-w-sm text-sm leading-relaxed text-ink">{describeLoadFailure(error)}</p>
      <Button variant="outline" size="sm" onClick={onRetry} className="mt-1">
        Retry
      </Button>
    </div>
  )
}

/** State 3 — empty. The register exists; nothing has been filed yet. */
function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-3 border border-rule bg-paper px-6 py-16 text-center">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/50">
        empty register
      </p>
      <p className="text-base font-semibold text-ink">No documents yet</p>
      <p className="max-w-sm text-sm leading-relaxed text-ink/60">
        Upload your first PDF and the pipeline will take it from there.
      </p>
      <Link href="/upload" className={cn(buttonVariants(), 'mt-1')}>
        Upload a document
      </Link>
    </div>
  )
}

interface PaginationProps {
  page: number
  total: number
  totalPages: number
  isFetching: boolean
  onPageChange: (page: number) => void
}

/**
 * Pagination — count line on the left, previous/next on the right. Buttons
 * disable while any fetch is in flight so rapid paging cannot queue stale
 * responses out of order. `aria-live` announces the page number change.
 * Controls hide entirely on a single-page register.
 */
function Pagination({ page, total, totalPages, isFetching, onPageChange }: PaginationProps) {
  return (
    <nav aria-label="Documents pages" className="flex items-center justify-between gap-4">
      <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink/50">
        {total} {total === 1 ? 'document' : 'documents'}
      </p>

      {totalPages > 1 ? (
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1 || isFetching}
            onClick={() => onPageChange(page - 1)}
          >
            Previous
          </Button>
          <span aria-live="polite" className="font-mono text-xs text-ink/60">
            page {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages || isFetching}
            onClick={() => onPageChange(page + 1)}
          >
            Next
          </Button>
        </div>
      ) : null}
    </nav>
  )
}
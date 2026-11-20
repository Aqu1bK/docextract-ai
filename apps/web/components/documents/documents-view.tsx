'use client'

import { useState } from 'react'

import { DocumentsTable } from '@/components/documents/documents-table'
import { useDocuments } from '@/lib/queries'

/** Server page size; kept in one place so the count line stays truthful. */
const PAGE_SIZE = 20

/**
 * DocumentsView — the stateful client shell of the documents page.
 *
 * Pagination lives here (not in the table) on purpose: page number is UI
 * state that must survive refetches and cache updates without being reset
 * by anything the query cache does. The view owns the number; the table
 * receives the live query plus the authoritative page and renders the
 * four states. Swapping the renderer later (a grid, infinite scroll)
 * would not touch this file's state logic.
 */
export function DocumentsView() {
  const [page, setPage] = useState(1)
  const documentsQuery = useDocuments({ page, pageSize: PAGE_SIZE })

  function handlePageChange(nextPage: number) {
    // Floor-clamp only; the upper bound is enforced by the disabled
    // next button, which knows totalPages from the data.
    setPage(Math.max(1, nextPage))
  }

  return (
    <div className="flex flex-col gap-4">
      <DocumentsTable query={documentsQuery} page={page} onPageChange={handlePageChange} />
    </div>
  )
}
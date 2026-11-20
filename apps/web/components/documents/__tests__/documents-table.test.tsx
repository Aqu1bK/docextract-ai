import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { UseQueryResult } from '@tanstack/react-query'

import { DocumentsTable } from '@/components/documents/documents-table'
import { ApiError } from '@/lib/api'
import type { DocumentSummary, Paginated } from '@/lib/api'

/**
 * DocumentsTable — the four states as plain data.
 *
 * The table takes the live query result as a prop, so tests never stand
 * up a QueryClient: each rendering state is expressed as a result object
 * handed straight to the component. That is the payoff of the prop-driven
 * design in the views layer.
 *
 * `@/lib/api` is mocked with a REAL ApiError class (not vi.fn): the
 * component branches on `error instanceof ApiError`, and the real module
 * cannot load in tests because it transitively imports env.ts, which
 * fail-fasts (zod) against a process.env the test runner does not
 * provide. The response-model types are type-only imports and never
 * reach the mock factory.
 */
vi.mock('@/lib/api', () => {
  /**
   * Mock ApiError mirrors the real 4-arg constructor exactly
   * (code, message, status, details), so the type imported at the top
   * of this file remains valid. Only `message` is asserted on by the
   * test; the other three args are accepted but unused.
   */
  class ApiError extends Error {
    readonly code: string
    readonly status: number
    readonly details: unknown

    constructor(code: string, message: string, status: number, details: unknown) {
      super(message)
      this.name = 'ApiError'
      this.code = code
      this.status = status
      this.details = details
    }
  }

  return { ApiError }
})

type DocumentsQuery = UseQueryResult<Paginated<DocumentSummary>, ApiError>

/**
 * Build a query result. The cast papering over the fields the table never
 * reads is deliberate — this factory owns exactly the surface the
 * component consumes: isPending / isError / isPlaceholderData /
 * isFetching / data / error / refetch.
 */
function makeQuery(overrides: Partial<DocumentsQuery> = {}): DocumentsQuery {
  return {
    isPending: false,
    isError: false,
    isSuccess: true,
    isFetching: false,
    isPlaceholderData: false,
    data: undefined,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  } as DocumentsQuery
}

const documentsFixture: DocumentSummary[] = [
  {
    id: '0192f0a1-0001-7000-8000-000000000001',
    filename: 'invoice-2026-001.pdf',
    content_type: 'application/pdf',
    size_bytes: 184320,
    page_count: 3,
    sha256: 'a1b2c3d4e5f6'.repeat(5).slice(0, 64), // 64-char hex placeholder
    status: 'needs_review',
    created_at: '2026-11-18T09:14:00Z',
  },
  {
    id: '0192f0a1-0002-7000-8000-000000000002',
    filename: 'contract-acme.pdf',
    content_type: 'application/pdf',
    size_bytes: 2369783,
    page_count: 12,
    sha256: 'b2c3d4e5f6a1'.repeat(5).slice(0, 64),
    status: 'approved',
    created_at: '2026-11-17T16:02:00Z',
  },
  {
    id: '0192f0a1-0003-7000-8000-000000000003',
    filename: 'receipt-nov.pdf',
    content_type: 'application/pdf',
    size_bytes: 51200,
    page_count: 1,
    sha256: 'c3d4e5f6a1b2'.repeat(5).slice(0, 64),
    status: 'queued',
    created_at: '2026-11-16T08:41:00Z',
  },
]

const pageFixture: Paginated<DocumentSummary> = {
  items: documentsFixture,
  total: 57,
  page: 1,
  page_size: 20,
  total_pages: 3,
}

describe('DocumentsTable', () => {
  it('renders the skeleton register while the first page is pending', () => {
    render(
      <DocumentsTable
        query={makeQuery({ isPending: true, isSuccess: false })}
        page={1}
        onPageChange={vi.fn()}
      />
    )

    // Polite status for assistive tech; the skeleton bars themselves are
    // aria-hidden by design.
    expect(screen.getByRole('status')).toHaveTextContent('Loading documents…')

    // Six placeholder rows x four columns. TableHead renders
    // columnheaders, so cell count isolates the skeleton body rows.
    expect(screen.getAllByRole('cell')).toHaveLength(6 * 4)
    expect(screen.queryByText('invoice-2026-001.pdf')).not.toBeInTheDocument()
  })

  it('renders the failure panel with the server message and retries on demand', async () => {
    const user = userEvent.setup()
    const refetch = vi.fn()
    const onPageChange = vi.fn()

    render(
      <DocumentsTable
        query={makeQuery({
          isError: true,
          isSuccess: false,
          error: new ApiError('HTTP_ERROR', 'The service is temporarily unavailable.', 503, null),
          refetch,
        })}
        page={3}
        onPageChange={onPageChange}
      />
    )

    // The ApiError branch of describeLoadFailure: server detail wins.
    expect(screen.getByRole('alert')).toHaveTextContent(
      'The service is temporarily unavailable.'
    )

    await user.click(screen.getByRole('button', { name: 'Retry' }))

    // Retry refetches; the view's pagination state is untouched — a
    // retry after paging resumes exactly where the user was.
    expect(refetch).toHaveBeenCalledTimes(1)
    expect(onPageChange).not.toHaveBeenCalled()
  })

  it('renders the empty state pointing at intake when the register has no documents', () => {
    render(
      <DocumentsTable
        query={makeQuery({
          data: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 },
        })}
        page={1}
        onPageChange={vi.fn()}
      />
    )

    expect(screen.getByText('No documents yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Upload a document' })).toHaveAttribute(
      'href',
      '/upload'
    )

    // No pagination chrome on a single empty page.
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
  })

  it('renders the register rows and drives paging through the callback', async () => {
    const user = userEvent.setup()
    const onPageChange = vi.fn()

    render(
      <DocumentsTable query={makeQuery({ data: pageFixture })} page={1} onPageChange={onPageChange} />
    )

    // One line per document, machine register contents.
    for (const document of documentsFixture) {
      expect(screen.getByText(document.filename)).toBeInTheDocument()
    }
    // formatBytes exercised in situ: 2,369,783 bytes -> "2.3 MB".
    expect(screen.getByText('2.3 MB')).toBeInTheDocument()
    expect(screen.getByText('Needs review')).toBeInTheDocument()
    expect(screen.getByText('Approved')).toBeInTheDocument()
    expect(screen.getByText('Queued')).toBeInTheDocument()

    // Count line and page indicator.
    expect(screen.getByText('57 documents')).toBeInTheDocument()
    expect(screen.getByText('page 1 / 3')).toBeInTheDocument()

    // Previous is clamped at the first page; Next advances the view.
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(onPageChange).toHaveBeenCalledWith(2)
  })
})
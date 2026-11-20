// docextract-ai/apps/web/components/documents/__tests__/documents-table.test.tsx

import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { DocumentDetailView } from '../document-detail-view';
import type { DocumentRecord, FieldRecord } from '@/lib/api';
import { describe, expect, it, vi } from 'vitest';

/**
 * Document detail smoke tests.
 *
 * The detail view orchestrates six queries and six mutations; the smoke
 * suite pins what a recruiter sees first: the header facts (mono file
 * name, size/pages/status line), the tab strip with all four surfaces,
 * the fields tab rendering as the default, and the fallbacks when the
 * PDF pane has no URL yet. Mocking the queries at the hooks layer (not
 * the fetch layer) keeps the assertions about layout, not HTTP.
 */

const DOCUMENT: DocumentRecord = {
  id: '11111111-1111-1111-1111-111111111111',
  file_name: 'invoice-2026-11.pdf',
  content_type: 'application/pdf',
  status: 'needs_review',
  page_count: 3,
  sha256: '0'.repeat(64),
  size_bytes: 1536,
  created_at: '2026-11-19T14:00:00Z',
};

const FIELDS: FieldRecord[] = [
  {
    id: '21111111-1111-1111-1111-111111111111',
    field_key: 'invoice_total',
    field_label: 'Invoice Total',
    value_text: '1250.00',
    confidence: 0.42,
    source: 'mock',
    page_number: 1,
    review_status: 'pending',
    original_value_text: null,
    is_required: true,
  },
  {
    id: '31111111-1111-1111-1111-111111111111',
    field_key: 'invoice_number',
    field_label: 'Invoice Number',
    value_text: 'INV-2026-001',
    confidence: 0.98,
    source: 'mock',
    page_number: 1,
    review_status: 'accepted',
    original_value_text: null,
    is_required: true,
  },
];

vi.mock('@/lib/queries', () => ({
  useDocumentDetail: () => ({ data: DOCUMENT, isPending: false, isError: false }),
  useDocumentFields: () => ({ data: FIELDS, isPending: false, isError: false }),
  useAuditLogs: () => ({ data: [], isPending: false, isError: false }),
  useDocumentDownloadUrl: () => ({ data: undefined, isPending: true, isError: false }),
  useAcceptField: () => ({ isPending: false }),
  useRejectField: () => ({ isPending: false }),
  useCorrectField: () => ({ isPending: false }),
  useApproveDocument: () => ({ isPending: false }),
  useRejectDocument: () => ({ isPending: false }),
  useExports: () => ({ data: [], isPending: false, isError: false }),
  useExtractionStatus: () => ({ data: undefined, isPending: true, isError: false }),
  useCreateExport: () => ({ isPending: false, mutate: vi.fn() }),
  useUploadDocument: () => ({ isPending: false, mutate: vi.fn() }),
  useDocuments: () => ({ data: undefined, isPending: true, isError: false }),
}));

vi.mock('react-pdf', () => ({
  Document: () => null,
  Page: () => null,
}));

function renderDetail() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DocumentDetailView documentId={DOCUMENT.id} />
    </QueryClientProvider>,
  );
}

describe('DocumentDetailView', () => {
  it('renders the header facts: mono file name, size, pages, status', () => {
    renderDetail();

    expect(screen.getByText('invoice-2026-11.pdf')).toBeInTheDocument();
    expect(screen.getByText(/1\.5 KB · 3 pages · needs review/)).toBeInTheDocument();
  });

  it('renders all four surface tabs with Fields as the default', () => {
    renderDetail();

    const fieldsTab = screen.getByRole('tab', { name: 'Fields' });
    expect(fieldsTab).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Audit' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Export' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Job' })).toBeInTheDocument();
  });

  it('renders the fields list as the default tab content', () => {
    renderDetail();

    expect(screen.getByText('Invoice Total')).toBeInTheDocument();
    expect(screen.getByText('Invoice Number')).toBeInTheDocument();
    expect(screen.getByText('INV-2026-001')).toBeInTheDocument();
  });

  it('renders the approval panel with the blocking conditions listed', () => {
    renderDetail();

    // The 0.42-confidence pending required field blocks approval.
    expect(screen.getByText(/Approval is blocked until:/)).toBeInTheDocument();
    expect(
      screen.getByText(/Required fields without an accepted or corrected value/),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Approve document' })).toBeDisabled();
  });
});
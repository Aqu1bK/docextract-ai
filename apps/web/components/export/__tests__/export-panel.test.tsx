import { render, screen } from '@testing-library/react';

import { ExportPanel } from '../export-panel';
import type { ExportRecord } from '@/lib/api';
import { describe, expect, it, vi } from 'vitest';

/**
 * Export panel tests.
 *
 * The export surface's honesty contract: the create buttons exist but
 * stay disabled until the document is approved (the backend would
 * reject anything else), the list of past exports renders each row's
 * facts, and a completed row carries the download link pointing at the
 * real endpoint. Hooks are mocked at the module layer so the assertions
 * stay about the panel, not the network.
 */

vi.mock('@/lib/queries', () => ({
  useExports: () => ({ data: EXPORTS, isPending: false, isError: false }),
  useCreateExport: () => ({
    isPending: false,
    variables: undefined,
    mutate: vi.fn(),
  }),
}));

const EXPORTS: ExportRecord[] = [
  {
    id: '61111111-1111-1111-1111-111111111111',
    format: 'json',
    status: 'completed',
    row_count: 3,
    expires_at: '2026-12-20T14:00:00Z',
    created_at: '2026-11-20T14:00:00Z',
    completed_at: '2026-11-20T14:00:01Z',
    error_message: null,
  },
  {
    id: '71111111-1111-1111-1111-111111111111',
    format: 'csv',
    status: 'failed',
    row_count: null,
    expires_at: null,
    created_at: '2026-11-19T09:00:00Z',
    completed_at: null,
    error_message: 'storage write failed',
  },
];

function renderPanel(documentStatus: string) {
  return render(
    <ExportPanel
      documentId="11111111-1111-1111-1111-111111111111"
      documentStatus={documentStatus}
    />,
  );
}

describe('ExportPanel', () => {
  it('disables both export buttons while the document is not approved', () => {
    renderPanel('needs_review');

    expect(screen.getByRole('button', { name: 'Export JSON' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeDisabled();
    expect(screen.getByText(/carry accepted and corrected fields only/)).toBeInTheDocument();
  });

  it('enables both export buttons once the document is approved', () => {
    renderPanel('approved');

    expect(screen.getByRole('button', { name: 'Export JSON' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeEnabled();
  });

  it('renders each past export row with its facts', () => {
    renderPanel('approved');

    expect(screen.getByText('json')).toBeInTheDocument();
    expect(screen.getByText('csv')).toBeInTheDocument();
    expect(screen.getByText('3 rows')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('failed')).toBeInTheDocument();
  });

  it('carries the download link on the completed export only', () => {
    renderPanel('approved');

    const download = screen.getByRole('link', { name: /download/i });
    expect(download).toHaveAttribute(
      'href',
      'http://localhost:8000/api/v1/documents/11111111-1111-1111-1111-111111111111/exports/61111111-1111-1111-1111-111111111111/download',
    );
    // The failed row shows its error, not a link.
    expect(screen.getByText('storage write failed')).toBeInTheDocument();
  });
});
'use client';

import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { ExportRow } from '@/components/export/export-row';
import { useCreateExport, useExports } from '@/lib/queries';

/**
 * ExportPanel — the export surface for one document.
 *
 * Two actions (JSON, CSV) and the list of past exports with download
 * links. The create mutation is disabled until the document is
 * approved — the backend would reject anything else with
 * VALIDATION_ERROR (document_not_approved), and a disabled state is
 * the honest UI for an impossible action, rather than a button that
 * fails. The list refreshes from the mutation's invalidation, so a
 * just-completed export appears with its download link immediately.
 */
export interface ExportPanelProps {
  /** The document being exported. */
  documentId: string;
  /** The document's status — export requires "approved". */
  documentStatus: string;
}

export function ExportPanel({ documentId, documentStatus }: ExportPanelProps) {
  const { data: exports, isPending } = useExports(documentId);
  const createExport = useCreateExport(documentId);

  const approved = documentStatus === 'approved';

  function handleCreate(format: 'json' | 'csv') {
    createExport.mutate(
      { format },
      {
        onSuccess: (result) => {
          toast.success(`Export ready — ${result.row_count ?? 0} rows.`);
        },
        onError: (error) => {
          toast.error(error instanceof Error ? error.message : 'Export failed.');
        },
      },
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          disabled={!approved || createExport.isPending}
          onClick={() => handleCreate('json')}
          title={approved ? undefined : 'Exporting requires an approved document'}
        >
          {createExport.isPending && createExport.variables?.format === 'json'
            ? 'Exporting…'
            : 'Export JSON'}
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={!approved || createExport.isPending}
          onClick={() => handleCreate('csv')}
          title={approved ? undefined : 'Exporting requires an approved document'}
        >
          {createExport.isPending && createExport.variables?.format === 'csv'
            ? 'Exporting…'
            : 'Export CSV'}
        </Button>
      </div>

      {!approved ? (
        <p className="text-xs text-ink-muted">
          Exports carry accepted and corrected fields only, and require an approved document.
        </p>
      ) : null}

      <div>
        {isPending ? (
          <div className="border border-rule bg-paper" aria-busy="true">
            {Array.from({ length: 2 }, (_, index) => (
              <div
                key={index}
                className="flex items-center gap-4 border-b border-rule px-3 py-2.5 last:border-b-0"
              >
                <div className="h-3 w-10 bg-paper-muted" />
                <div className="h-3 w-16 bg-paper-muted" />
                <div className="ml-auto h-3 w-20 bg-paper-muted" />
              </div>
            ))}
          </div>
        ) : (exports ?? []).length === 0 ? (
          <div className="border border-rule bg-paper p-4">
            <p className="text-sm text-ink-muted">No exports yet.</p>
            <p className="mt-1 text-xs text-ink-muted">
              Approve the document, then export its reviewed data as JSON or CSV.
            </p>
          </div>
        ) : (
          <ul className="border border-rule bg-paper">
            {(exports ?? []).map((exportRecord) => (
              <ExportRow
                key={exportRecord.id}
                exportRecord={exportRecord}
                documentId={documentId}
              />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

import { AuditTimeline } from '@/components/audit/audit-timeline';
import { DocumentActions } from '@/components/review/document-actions';
import { FieldList } from '@/components/review/field-list';
import { ExportPanel } from '@/components/export/export-panel';
import { JobStatusTab } from '@/components/jobs/job-status-tab';
import { PdfViewer } from '@/components/pdf/pdf-viewer';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { formatBytes } from '@/components/documents/document-row';
import { useAuditLogs, useDocumentDetail, useDocumentFields } from '@/lib/queries';
import { useDocumentDownloadUrl } from '@/lib/queries';

/**
 * DocumentDetailView — the review surface, one screen, four tabs.
 *
 * Layout: the document's own paper on the left (the PDF the machine
 * read), the human's work on the right — a tab strip switching between
 * Fields (the review queue's verdicts), Audit (the append-only trail),
 * Export (approved data out), and Job (the pipeline's own status). The
 * tab strip is the deliberate design: a reviewer's attention moves
 * between the document and exactly one working surface at a time, so
 * the two-column frame holds paper still and changes the work pane.
 *
 * The PDF's source URL is the one thing the backend does not serve on
 * the documents router: it is fetched through a query hook (a signed
 * read) so the viewer re-renders when a refreshed URL arrives. Until
 * then the pane holds its loading frame.
 */
const TABS = [
  { key: 'fields', label: 'Fields' },
  { key: 'audit', label: 'Audit' },
  { key: 'export', label: 'Export' },
  { key: 'job', label: 'Job' },
] as const;

type TabKey = (typeof TABS)[number]['key'];

export function DocumentDetailView({ documentId }: { documentId: string }) {
  const [tab, setTab] = useState<TabKey>('fields');

  const document = useDocumentDetail(documentId);
  const fields = useDocumentFields(documentId);
  const auditLogs = useAuditLogs(documentId);
  const downloadUrl = useDocumentDownloadUrl(documentId);

  if (document.isError) {
    return (
      <div className="border border-rule bg-paper p-8 text-center">
        <p className="text-sm text-ink">This document could not be loaded.</p>
        <Button variant="outline" size="sm" className="mt-4" asChild>
          <Link href="/documents">Back to documents</Link>
        </Button>
      </div>
    );
  }

  const doc = document.data;

  return (
    <div className="space-y-6">
      {/* Header: back to the register, then the document's identity. */}
      <div>
        <Button variant="outline" size="sm" asChild>
          <Link href="/documents">
            <ArrowLeft className="size-3.5" aria-hidden />
            Documents
          </Link>
        </Button>

        <div className="mt-3 flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h1 className="font-mono text-xl font-semibold tracking-tight text-ink">
              {doc?.file_name ?? '…'}
            </h1>
            <p className="mt-1 text-sm text-ink-muted">
              {doc !== undefined
                ? `${formatBytes(doc.size_bytes)}${doc.page_count !== null ? ` · ${doc.page_count} page${doc.page_count === 1 ? '' : 's'}` : ''} · ${doc.status.replace(/_/g, ' ')}`
                : 'Loading document…'}
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        {/* Left: the paper itself. */}
        <div className="min-w-0">
          <div className="border border-rule bg-paper p-3">
            <p className="px-1 pb-3 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Source document
            </p>
            {downloadUrl.data !== undefined ? (
              <PdfViewer url={downloadUrl.data} />
            ) : downloadUrl.isError ? (
              <div className="border border-rule bg-paper-muted p-8 text-center">
                <p className="text-sm text-ink">The source PDF is not viewable here.</p>
                <p className="mt-1 text-xs text-ink-muted">
                  File retrieval is unavailable — the review fields below still show what the
                  machine extracted.
                </p>
              </div>
            ) : (
              <div className="h-96 bg-paper-muted" aria-busy="true" aria-label="Loading PDF" />
            )}
          </div>
        </div>

        {/* Right: the human's work pane, one tab at a time. */}
        <div className="min-w-0">
          <div role="tablist" aria-label="Document surfaces" className="flex border-b border-rule">
            {TABS.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={tab === key}
                onClick={() => setTab(key)}
                className={cn(
                  'border border-b-0 border-rule bg-paper px-4 py-2 text-sm transition-colors',
                  tab === key
                    ? 'font-semibold text-ink [box-shadow:inset_0_2px_0_var(--color-accent)]'
                    : 'text-ink-muted hover:text-ink',
                  tab !== key && 'mr-2',
                )}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="border border-t-0 border-rule bg-paper p-4">
            {tab === 'fields' ? (
              <FieldList fields={fields.data ?? []} documentId={documentId} />
            ) : null}
            {tab === 'audit' ? <AuditTimeline logs={auditLogs.data ?? []} /> : null}
            {tab === 'export' ? (
              <ExportPanel documentId={documentId} documentStatus={doc?.status ?? ''} />
            ) : null}
            {tab === 'job' ? <JobStatusTab documentId={documentId} /> : null}
          </div>

          {/* The document-level verdict lives below the tabs: it is the
              decision the fields' individual verdicts add up to. */}
          <div className="mt-4">
            <DocumentActions
              documentId={documentId}
              documentStatus={doc?.status ?? ''}
              fields={fields.data ?? []}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
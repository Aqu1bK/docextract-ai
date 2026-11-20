'use client';

import { Badge } from '@/components/ui/badge';
import { useExtractionStatus } from '@/lib/queries';

/**
 * JobStatusTab — the queue's window: document status + latest job.
 *
 * While the document is mid-pipeline (uploaded, queued, processing) the
 * hook polls every 3 seconds via TanStack's refetchInterval; once the
 * document reaches a terminal status the interval callback returns
 * false and polling stops — a page left open in a tab does not poll a
 * settled pipeline forever. The job rows render attempts against the
 * ceiling and the failure codes, the two facts that distinguish "slow"
 * from "stuck" from "dead".
 */
export interface JobStatusTabProps {
  /** The document whose extraction status is shown. */
  documentId: string;
}

export function JobStatusTab({ documentId }: JobStatusTabProps) {
  const { data, isPending, isError, refetch } = useExtractionStatus(documentId);

  if (isPending) {
    return (
      <div className="border border-rule bg-paper p-4 text-sm text-ink-muted" aria-busy="true">
        Loading extraction status…
      </div>
    );
  }

  if (isError || data === undefined) {
    return (
      <div className="border border-rule bg-paper p-4">
        <p className="text-sm text-ink">Could not load the extraction status.</p>
        <p className="mt-1 text-xs text-ink-muted">The backend may be unreachable.</p>
        <button
          type="button"
          className="mt-3 border border-rule bg-paper px-2 py-1 text-sm text-ink transition-colors hover:bg-paper-muted"
          onClick={() => void refetch()}
        >
          Retry
        </button>
      </div>
    );
  }

  const job = data.latest_job;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <span className="text-sm text-ink">Document status:</span>
        <Badge variant="outline">{data.document_status.replace(/_/g, ' ')}</Badge>
      </div>

      {job === null ? (
        <p className="text-xs text-ink-muted">
          No extraction job yet — extraction starts after the upload is confirmed.
        </p>
      ) : (
        <div className="flex flex-col gap-2 border border-rule bg-paper p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-ink">Latest job:</span>
            <Badge variant="outline">{job.status.replace(/_/g, ' ')}</Badge>
            <span className="font-mono text-xs text-ink-muted">
              attempts {job.attempts} / {job.max_attempts}
            </span>
          </div>

          {job.error_code !== null ? (
            <p className="font-mono text-xs text-confidence-low">{job.error_code}</p>
          ) : null}
          {job.error_message !== null ? (
            <p className="text-xs text-ink-muted">{job.error_message}</p>
          ) : null}

          <p className="text-xs text-ink-muted">
            {job.status === 'succeeded' || job.completed_at !== null
              ? "The run that produced this document's data."
              : 'This tab refreshes every few seconds until the pipeline settles.'}
          </p>
        </div>
      )}
    </div>
  );
}
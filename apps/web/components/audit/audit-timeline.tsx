'use client';

import { AuditEvent } from '@/components/audit/audit-event';
import type { AuditLogRecord } from '@/lib/api';

/**
 * AuditTimeline — the document's history as a vertical rail.
 *
 * The vertical timeline pattern: one hairline rail down the left edge
 * (a 1px border, not a drawn line), each event a square dot on the
 * rail with its timestamp and description. The backend returns rows
 * newest-first; the timeline renders them in that order — the most
 * recent decision sits at the top, where a reviewer catching up reads
 * first. An empty trail renders an honest empty state instead of a
 * bare rail.
 */
export interface AuditTimelineProps {
  /** Audit rows for one document, newest first (backend order). */
  logs: AuditLogRecord[];
}

export function AuditTimeline({ logs }: AuditTimelineProps) {
  if (logs.length === 0) {
    return (
      <div className="border border-rule bg-paper p-4">
        <p className="text-sm text-ink-muted">No audit entries yet.</p>
        <p className="mt-1 text-xs text-ink-muted">
          Every review decision, approval, and export lands here as it happens.
        </p>
      </div>
    );
  }

  return (
    <ol className="relative border-l border-rule pl-6" aria-label="Audit timeline">
      {logs.map((log) => (
        <AuditEvent key={log.id} log={log} />
      ))}
    </ol>
  );
}
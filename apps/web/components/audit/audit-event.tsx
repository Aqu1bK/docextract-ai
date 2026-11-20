'use client';

import type { AuditLogRecord } from '@/lib/api';

/**
 * AuditEvent — one entry on the audit timeline.
 *
 * The dot + timestamp + description pattern: a square dot (this system
 * has no circles) sits on the timeline's hairline rail, the action's
 * verb renders as the entry's title, and the actor + time run in the
 * muted line beneath. `metadata_json` is not dumped — an auditor reads
 * structured context selectively, so the two most common keys (field,
 * reason) surface as prose when present.
 */
export interface AuditEventProps {
  /** The audit row to render. */
  log: AuditLogRecord;
}

/** Format an audit timestamp as "Nov 20, 14:32" — timeline precision. */
function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function AuditEvent({ log }: AuditEventProps) {
  // A dot-separated verb ("field.corrected") reads as a timeline title
  // with the category first: "field — corrected".
  const [category, verb] = log.action.includes('.') ? log.action.split('.', 2) : [log.action, ''];

  const reason = typeof log.metadata_json.reason === 'string' ? log.metadata_json.reason : null;
  const fieldKey =
    typeof log.metadata_json.field_key === 'string' ? log.metadata_json.field_key : null;

  return (
    <li className="relative pl-6 pb-4 last:pb-0">
      {/* The square dot on the rail — ink for human actions, muted for
          system rows (a worker finishing a job has no actor). */}
      <span
        aria-hidden
        className={`absolute left-0 top-1 size-2 ${
          log.actor_user_id === null ? 'bg-rule' : 'bg-ink'
        }`}
      />
      <div className="flex flex-wrap items-baseline gap-x-2">
        <span className="text-sm font-medium text-ink">
          {category}
          {verb ? ` — ${verb}` : ''}
        </span>
        <span className="font-mono text-xs text-ink-muted">{formatTimestamp(log.created_at)}</span>
      </div>
      <p className="mt-1 text-xs text-ink-muted">
        {log.actor_user_id === null ? 'system' : 'reviewer'} · {log.entity_type}
        {fieldKey !== null ? ` · ${fieldKey}` : ''}
      </p>
      {reason !== null ? <p className="mt-1 text-xs text-ink">reason: {reason}</p> : null}
    </li>
  );
}
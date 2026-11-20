// docextract-ai/apps/web/components/review/field-row.tsx

'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { FieldRecord } from '@/lib/api';

/**
 * FieldRow — one extracted field with its confidence and review actions.
 *
 * The reviewer's unit of work. The row shows what the machine produced
 * (the mono value, the confidence badge), what the human decided (the
 * status badge), and offers the three decisions: Accept (endorse the
 * machine value), Correct (replace it, inline), Reject (dismiss it and
 * clear the value). The correction form's open state and the mutations
 * live in the parent (FieldList); this row reports intent upward, so
 * the row itself never holds server state.
 *
 * `original_value_text` renders only after a correction or rejection
 * overwrote/cleared the machine value — the row then shows both voices,
 * machine first, human second, in the provenance typography the design
 * system assigns (mono for machine output).
 */
export interface FieldRowProps {
  /** The field to render. */
  field: FieldRecord;
  /** Whether this row's correction form is open (parent owns the state). */
  isCorrecting?: boolean;
  /** Disabled while a mutation is in flight (buttons lock). */
  isPending?: boolean;
  /** Instruct parent to accept the field's machine value. */
  onAccept: (fieldId: string) => void;
  /** Instruct parent to reject the field (clears its value). */
  onReject: (fieldId: string) => void;
  /** Instruct parent to open/close this row's correction form. */
  onToggleCorrect: () => void;
}

/** Confidence thresholds mirroring the backend's CONFIDENCE_THRESHOLD=0.75. */
function confidenceVariant(confidence: number): 'confidence-high' | 'confidence-mid' | 'confidence-low' {
  if (confidence >= 0.9) return 'confidence-high';
  if (confidence >= 0.75) return 'confidence-mid';
  return 'confidence-low';
}

/**
 * Review status → Badge variant: one badge variant per FieldReviewStatus
 * enum value, keyed explicitly so the variant union stays compile-time
 * (a template string would widen past it).
 */
const STATUS_VARIANT: Record<string, 'status-pending' | 'status-accepted' | 'status-corrected' | 'status-rejected' | 'status-missing'> = {
  pending: 'status-pending',
  accepted: 'status-accepted',
  corrected: 'status-corrected',
  rejected: 'status-rejected',
  missing: 'status-missing',
};

export function FieldRow({
  field,
  isCorrecting = false,
  isPending = false,
  onAccept,
  onReject,
  onToggleCorrect,
}: FieldRowProps) {
  const decided = field.review_status !== 'pending';

  return (
    <div className="border-b border-rule px-3 py-4 last:border-b-0">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-ink">{field.field_label}</span>
            <Badge variant={confidenceVariant(field.confidence)}>
              {field.confidence.toFixed(2)}
            </Badge>
            {decided ? (
              <Badge variant={STATUS_VARIANT[field.review_status] ?? 'status-pending'}>
                {field.review_status}
              </Badge>
            ) : null}
            {field.is_required ? <Badge variant="outline">required</Badge> : null}
          </div>

          <div className="mt-2 truncate font-mono text-sm text-ink" title={field.value_text ?? undefined}>
            {field.value_text ?? <span className="text-ink-muted">(no value)</span>}
          </div>

          {field.original_value_text !== null ? (
            <div className="mt-1 truncate font-mono text-xs text-ink-muted" title={field.original_value_text}>
              machine: {field.original_value_text}
            </div>
          ) : null}
        </div>

        <div className="flex shrink-0 gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={isPending || decided}
            onClick={() => onAccept(field.id)}
          >
            Accept
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={isPending}
            onClick={onToggleCorrect}
          >
            {isCorrecting ? 'Cancel' : 'Correct'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={isPending || decided}
            onClick={() => onReject(field.id)}
          >
            Reject
          </Button>
        </div>
      </div>
    </div>
  );
}
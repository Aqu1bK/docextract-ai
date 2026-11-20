'use client';

import { useState } from 'react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { FieldRecord } from '@/lib/api';
import { useApproveDocument, useRejectDocument } from '@/lib/queries';

/**
 * DocumentActions — the document-level verdict: approve or reject.
 *
 * Approval is earned, not clicked: the backend's APPROVAL_BLOCKED 409
 * carries a machine-readable `blockers` list, and this panel renders
 * the same two conditions the backend checks (required fields
 * unresolved; low-confidence fields still pending) from the live
 * field data, so the reviewer sees exactly what stands between them
 * and approval BEFORE the button fails. The blocking-condition rows
 * are computed client-side from the same rule the backend enforces
 * server-side — display only, never enforcement.
 *
 * Rejection is always available for a reviewable document and takes
 * an optional reason that lands in the audit trail verbatim.
 */
export interface DocumentActionsProps {
  /** The document's current status (drives which verdicts are offered). */
  documentStatus: string;
  /** The document's fields, from which blocking conditions are computed. */
  fields: FieldRecord[];
  /** The document whose verdict these buttons record. */
  documentId: string;
}

/** The backend's CONFIDENCE threshold; mirrored here for display only. */
const CONFIDENCE_THRESHOLD = 0.75;

/** The two blocking conditions the backend's approval gate checks. */
export function computeBlockers(fields: FieldRecord[]): string[] {
  const requiredUnresolved = fields.some(
    (field) => field.is_required && !['accepted', 'corrected'].includes(field.review_status),
  );
  const lowConfidencePending = fields.some(
    (field) => field.confidence < CONFIDENCE_THRESHOLD && field.review_status === 'pending',
  );
  const blockers: string[] = [];
  if (requiredUnresolved) blockers.push('required_fields_unresolved');
  if (lowConfidencePending) blockers.push('low_confidence_fields_unresolved');
  return blockers;
}

/** Human-readable copy for each machine-readable blocker code. */
const BLOCKER_COPY: Record<string, string> = {
  required_fields_unresolved: 'Required fields without an accepted or corrected value.',
  low_confidence_fields_unresolved: 'Low-confidence fields still awaiting review.',
};

export function DocumentActions({ documentStatus, fields, documentId }: DocumentActionsProps) {
  const [isRejecting, setIsRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const approveDocument = useApproveDocument(documentId);
  const rejectDocument = useRejectDocument(documentId);

  const reviewable = documentStatus === 'needs_review' || documentStatus === 'ready_for_review';
  const blockers = computeBlockers(fields);
  const approvable = blockers.length === 0;

  function handleApprove() {
    approveDocument.mutate(undefined, {
      onSuccess: () => {
        toast.success('Document approved — export is now available.');
      },
      onError: (error) => {
        toast.error(error instanceof Error ? error.message : 'Approval failed.');
      },
    });
  }

  function handleReject() {
    rejectDocument.mutate(
      { reason: rejectReason === '' ? undefined : rejectReason },
      {
        onSuccess: () => {
          setIsRejecting(false);
          setRejectReason('');
          toast.success('Document rejected.');
        },
        onError: (error) => {
          toast.error(error instanceof Error ? error.message : 'Rejection failed.');
        },
      },
    );
  }

  if (!reviewable) {
    return (
      <div className="border border-rule bg-paper p-4">
        <p className="text-sm text-ink-muted">
          This document is {documentStatus.replace('_', ' ')} — the review verdict is closed.
        </p>
      </div>
    );
  }

  return (
    <div className="border border-rule bg-paper p-4">
      <div className="flex flex-col gap-3">
        {blockers.length > 0 ? (
          <div className="border border-rule bg-paper-muted p-3">
            <p className="text-xs font-semibold text-ink">Approval is blocked until:</p>
            <ul className="mt-2 space-y-1">
              {blockers.map((blocker) => (
                <li key={blocker} className="flex items-center gap-2 text-xs text-ink-muted">
                  <Badge variant="status-rejected">blocked</Badge>
                  {BLOCKER_COPY[blocker] ?? blocker}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-xs text-ink-muted">
            Every field is resolved — approval will certify the reviewed data.
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            disabled={!approvable || approveDocument.isPending}
            onClick={handleApprove}
          >
            {approveDocument.isPending ? 'Approving…' : 'Approve document'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={rejectDocument.isPending}
            onClick={() => setIsRejecting((r) => !r)}
          >
            {isRejecting ? 'Cancel rejection' : 'Reject document'}
          </Button>
        </div>

        {isRejecting ? (
          <div className="space-y-2 border border-rule bg-paper-muted p-3">
            <Label htmlFor={`reject-reason-${documentId}`}>Reason (optional)</Label>
            <Input
              id={`reject-reason-${documentId}`}
              type="text"
              value={rejectReason}
              onChange={(event) => setRejectReason(event.target.value)}
              placeholder="Why the extraction is unusable"
            />
            <Button
              variant="outline"
              size="sm"
              disabled={rejectDocument.isPending}
              onClick={handleReject}
            >
              {rejectDocument.isPending ? 'Rejecting…' : 'Confirm rejection'}
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
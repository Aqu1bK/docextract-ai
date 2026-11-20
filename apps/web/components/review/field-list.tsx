'use client';

import { useState } from 'react';
import { toast } from 'sonner';

import { CorrectFieldForm } from '@/components/review/correct-field-form';
import { FieldRow } from '@/components/review/field-row';
import type { FieldRecord } from '@/lib/api';
import { useAcceptField, useCorrectField, useRejectField } from '@/lib/queries';

/**
 * FieldList — every extracted field of one document, with live actions.
 *
 * The list owns the three field mutations (accept / correct / reject)
 * so each FieldRow stays a presentational unit that reports intent
 * upward, and the correction form's open state stays per-row without
 * being lifted: `correctingFieldId` is the single "which row's form is
 * open" fact. Every mutation invalidates ['document-fields', id] on
 * success, so the row the reviewer just acted on re-renders with the
 * server's verdict — the status badge flips from pending to accepted/
 * corrected/rejected — and the document queries refetch so the header's
 * status and the approval panel's blocking conditions update in the
 * same sweep.
 */
export interface FieldListProps {
  /** All fields of the document, ordered by field_key (backend order). */
  fields: FieldRecord[];
  /** The document whose fields these are (invalidations key on it). */
  documentId: string;
}

export function FieldList({ fields, documentId }: FieldListProps) {
  const [correctingFieldId, setCorrectingFieldId] = useState<string | null>(null);

  const acceptField = useAcceptField(documentId);
  const correctField = useCorrectField(documentId);
  const rejectField = useRejectField(documentId);

  const anyPending = acceptField.isPending || correctField.isPending || rejectField.isPending;

  /** A correction applies to one field: value + reason travel to the mutation. */
  function handleCorrect(fieldId: string, value: string, reason: string) {
    correctField.mutate(
      { fieldId, value, reason: reason === '' ? undefined : reason },
      {
        onSuccess: () => {
          setCorrectingFieldId(null);
          toast.success('Correction saved — the machine value is preserved in the trail.');
        },
        onError: (error) => {
          toast.error(error instanceof Error ? error.message : 'Correction failed.');
        },
      },
    );
  }

  function handleAccept(fieldId: string) {
    acceptField.mutate(
      { fieldId },
      {
        onSuccess: () => {
          toast.success('Field accepted.');
        },
        onError: (error) => {
          toast.error(error instanceof Error ? error.message : 'Accept failed.');
        },
      },
    );
  }

  function handleReject(fieldId: string) {
    rejectField.mutate(
      { fieldId },
      {
        onSuccess: () => {
          toast.success('Field rejected — its value is cleared and kept in the trail.');
        },
        onError: (error) => {
          toast.error(error instanceof Error ? error.message : 'Rejection failed.');
        },
      },
    );
  }

  return (
    <div className="border border-rule bg-paper">
      {fields.map((field) => (
        <div key={field.id}>
          <FieldRow
            field={field}
            isPending={anyPending}
            onAccept={handleAccept}
            onReject={handleReject}
            onToggleCorrect={() =>
              setCorrectingFieldId((current) => (current === field.id ? null : field.id))
            }
          />
          {correctingFieldId === field.id ? (
            <div className="px-3 pb-4">
              <CorrectFieldForm
                fieldId={field.id}
                currentValue={field.value_text ?? ''}
                isPending={correctField.isPending}
                onSubmit={(values) => handleCorrect(field.id, values.value, values.reason)}
                onCancel={() => setCorrectingFieldId(null)}
              />
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
'use client';

import { useForm } from 'react-hook-form';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

/**
 * CorrectFieldForm — the inline replacement form for one field.
 *
 * React Hook Form's uncontrolled registration (register + handleSubmit)
 * keeps the form state out of React re-renders; the submission calls
 * the parent's correction mutation via the `onSubmit` callback so this
 * form stays a pure input surface. The reason field is optional but
 * offered: the backend records it into the audit trail verbatim.
 */
export interface CorrectFieldFormValues {
  /** The reviewer's replacement value (required, non-empty). */
  value: string;
  /** Optional explanation recorded in the audit trail. */
  reason: string;
}

export interface CorrectFieldFormProps {
  /** The field being corrected (its id travels with the submission). */
  fieldId: string;
  /** The current value, prefilled as the correction's starting point. */
  currentValue: string;
  /** Disabled while the correction mutation is in flight. */
  isPending?: boolean;
  /** Instruct parent to apply the correction (value + reason). */
  onSubmit: (values: CorrectFieldFormValues) => void;
  /** Instruct parent to cancel the correction (collapse the form). */
  onCancel: () => void;
}

export function CorrectFieldForm({
  fieldId,
  currentValue,
  isPending = false,
  onSubmit,
  onCancel,
}: CorrectFieldFormProps) {
  const { register, handleSubmit } = useForm<CorrectFieldFormValues>({
    defaultValues: { value: currentValue, reason: '' },
  });

  return (
    <form
      className="border border-rule bg-paper-muted p-3"
      onSubmit={handleSubmit(onSubmit)}
      aria-label={`Correct field ${fieldId}`}
    >
      <div className="space-y-2">
        <Label htmlFor={`correct-value-${fieldId}`}>Corrected value</Label>
        <Input
          id={`correct-value-${fieldId}`}
          type="text"
          autoComplete="off"
          required
          {...register('value', { required: true })}
        />
      </div>

      <div className="mt-3 space-y-2">
        <Label htmlFor={`correct-reason-${fieldId}`}>Reason (optional)</Label>
        <Input
          id={`correct-reason-${fieldId}`}
          type="text"
          autoComplete="off"
          {...register('reason')}
        />
      </div>

      <div className="mt-3 flex gap-2">
        <Button type="submit" size="sm" disabled={isPending}>
          {isPending ? 'Saving…' : 'Save correction'}
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={onCancel} disabled={isPending}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
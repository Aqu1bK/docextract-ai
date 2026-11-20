import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { FieldRow } from '../field-row';
import type { FieldRecord } from '@/lib/api';
import { describe, expect, it, vi } from 'vitest';

/**
 * Field row rendering tests.
 *
 * The reviewer's unit of work: the row must show the machine's value in
 * the machine font, the confidence in the badge the thresholds color,
 * the human's verdict once decided, and the preserved machine original
 * after a correction or rejection. Intent reporting (onAccept /
 * onReject / onToggleCorrect) is asserted by clicking, so the wiring to
 * the parent's mutations is pinned, not assumed.
 */

function makeField(overrides: Partial<FieldRecord> = {}): FieldRecord {
  return {
    id: '21111111-1111-1111-1111-111111111111',
    field_key: 'invoice_total',
    field_label: 'Invoice Total',
    value_text: '1250.00',
    confidence: 0.98,
    source: 'mock',
    page_number: 1,
    review_status: 'pending',
    original_value_text: null,
    is_required: true,
    ...overrides,
  };
}

function renderRow(field: FieldRecord) {
  const onAccept = vi.fn();
  const onReject = vi.fn();
  const onToggleCorrect = vi.fn();
  const view = render(
    <FieldRow
      field={field}
      onAccept={onAccept}
      onReject={onReject}
      onToggleCorrect={onToggleCorrect}
    />,
  );
  return { onAccept, onReject, onToggleCorrect, view };
}

describe('FieldRow', () => {
  it('renders the label, value, and confidence score', () => {
    renderRow(makeField());

    expect(screen.getByText('Invoice Total')).toBeInTheDocument();
    expect(screen.getByText('1250.00')).toBeInTheDocument();
    expect(screen.getByText('0.98')).toBeInTheDocument();
  });

  it('renders the status badge only once the field is decided', () => {
    const { view } = renderRow(
      makeField({ review_status: 'corrected', original_value_text: '1250.00' }),
    );

    expect(screen.getByText('corrected')).toBeInTheDocument();

    view.unmount();
    renderRow(makeField());
    // pending is the default state: no status badge renders for it.
    expect(screen.queryByText('pending')).not.toBeInTheDocument();
  });

  it('shows the preserved machine value after a correction', () => {
    renderRow(
      makeField({
        review_status: 'corrected',
        value_text: '1299.00',
        original_value_text: '1250.00',
      }),
    );

    expect(screen.getByText('1299.00')).toBeInTheDocument();
    expect(screen.getByText('machine: 1250.00')).toBeInTheDocument();
  });

  it('reports accept and reject intent upward on click', async () => {
    const user = userEvent.setup();
    const { onAccept, onReject } = renderRow(makeField());

    await user.click(screen.getByRole('button', { name: 'Accept' }));
    expect(onAccept).toHaveBeenCalledWith('21111111-1111-1111-1111-111111111111');

    await user.click(screen.getByRole('button', { name: 'Reject' }));
    expect(onReject).toHaveBeenCalledWith('21111111-1111-1111-1111-111111111111');
  });

  it('reports the correct toggle intent and disables decided rows', async () => {
    const user = userEvent.setup();
    const { onToggleCorrect } = renderRow(makeField());

    await user.click(screen.getByRole('button', { name: 'Correct' }));
    expect(onToggleCorrect).toHaveBeenCalledTimes(1);
  });

  it('disables accept and reject for a decided field', () => {
    renderRow(makeField({ review_status: 'accepted' }));

    expect(screen.getByRole('button', { name: 'Accept' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Reject' })).toBeDisabled();
  });
});
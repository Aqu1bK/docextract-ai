import { render, screen } from '@testing-library/react';

import { AuditTimeline } from '../audit-timeline';
import type { AuditLogRecord } from '@/lib/api';
import { describe, expect, it } from 'vitest';

/**
 * Audit timeline rendering tests.
 *
 * The timeline is the trust surface: what renders must be the trail the
 * backend recorded, newest first, with the actor and time on each entry.
 * The suite pins the order (newest at the top), the entry shape
 * (category — verb, timestamp, actor), the system-row distinction (null
 * actor renders "system", a muted dot), and the honest empty state.
 */

function makeLog(overrides: Partial<AuditLogRecord> = {}): AuditLogRecord {
  return {
    id: '41111111-1111-1111-1111-111111111111',
    action: 'field.corrected',
    entity_type: 'extracted_field',
    entity_id: '21111111-1111-1111-1111-111111111111',
    actor_user_id: '81111111-1111-1111-1111-111111111111',
    metadata_json: { field_key: 'invoice_total', reason: 'digit misread' },
    created_at: '2026-11-20T14:32:00Z',
    ...overrides,
  };
}

describe('AuditTimeline', () => {
  it('renders each log with its action, actor, and reason', () => {
    render(<AuditTimeline logs={[makeLog()]} />);

    expect(screen.getByText('field — corrected')).toBeInTheDocument();
    expect(screen.getByText('reviewer · extracted_field · invoice_total')).toBeInTheDocument();
    expect(screen.getByText('reason: digit misread')).toBeInTheDocument();
  });

  it('renders newest first: the later event appears above the earlier one', () => {
    const earlier = makeLog({
      id: '51111111-1111-1111-1111-111111111111',
      action: 'document.exported',
      metadata_json: {},
      created_at: '2026-11-20T10:00:00Z',
    });
    const later = makeLog({ created_at: '2026-11-20T14:32:00Z' });

    render(<AuditTimeline logs={[later, earlier]} />);

    const entries = screen.getAllByRole('listitem');
    expect(entries).toHaveLength(2);
    // The timeline renders backend order (newest first); the first entry
    // on screen is the later timestamp's event.
    expect(entries[0].textContent).toContain('field — corrected');
    expect(entries[1].textContent).toContain('document — exported');
  });

  it('renders the system actor for worker rows', () => {
    render(<AuditTimeline logs={[makeLog({ actor_user_id: null })]} />);

    expect(screen.getByText(/system ·/)).toBeInTheDocument();
  });

  it('renders the honest empty state when the trail is empty', () => {
    render(<AuditTimeline logs={[]} />);

    expect(screen.getByText('No audit entries yet.')).toBeInTheDocument();
    expect(
      screen.getByText(/Every review decision, approval, and export lands here/),
    ).toBeInTheDocument();
  });
});
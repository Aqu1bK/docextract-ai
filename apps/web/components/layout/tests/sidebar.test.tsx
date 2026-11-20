// docextract-ai/apps/web/components/layout/tests/sidebar.test.tsx

import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Sidebar } from '../sidebar'

const TEST_EMAIL = 'test@example.com'
const TEST_ROLES = ['reviewer']

/**
 * Sidebar — smoke tests against the Phase 9B rewrite.
 *
 * Key behavior changes from 9A that the tests must reflect:
 *   1. Brand mark is a <div> (not a <Link>) — query by text, not role.
 *   2. Collapse is CSS-only (`hidden lg:inline`) — labels stay in the
 *      DOM at every viewport; jsdom cannot evaluate responsive CSS,
 *      so "collapsed" is not a testable DOM state. We assert the
 *      labels exist with the hidden utility class instead.
 *   3. Email + role come from props — assert the passed values, not
 *      a hardcoded fixture.
 *
 * `usePathname` is stubbed to /dashboard so the Dashboard item gets
 * `aria-current="page"` and we can verify the active-state wiring.
 */

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
}))

describe('Sidebar', () => {
  it('renders the brand, all six destinations, and the session footer', () => {
    render(<Sidebar userEmail={TEST_EMAIL} userRoles={TEST_ROLES} />)

    // Brand mark — a div with the glyph and product name (not a link).
    expect(screen.getByText('Dx')).toBeInTheDocument()
    expect(screen.getByText('DocExtract AI')).toBeInTheDocument()

    // All six nav destinations render.
    const destinations = [
      'Dashboard',
      'Documents',
      'Upload',
      'Review',
      'Exports',
      'Audit',
    ]
    for (const label of destinations) {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument()
    }

    // Active-route wiring: pathname is stubbed to /dashboard.
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute(
      'aria-current',
      'page',
    )

    // Session footer renders the passed email + first role.
    expect(screen.getByText(TEST_EMAIL)).toBeInTheDocument()
    expect(screen.getByText(TEST_ROLES[0])).toBeInTheDocument()
  })

  it('keeps all nav labels in the DOM (CSS-only collapse)', () => {
    // 9B uses CSS-only collapse (`hidden lg:inline`) — labels stay in
    // the DOM at every viewport. jsdom cannot evaluate responsive CSS,
    // so "collapsed" is not a testable DOM state; we assert the
    // labels exist and carry the hidden utility class.
    render(<Sidebar userEmail={TEST_EMAIL} userRoles={TEST_ROLES} />)

    const documentsLink = screen.getByRole('link', { name: 'Documents' })
    const labelSpan = documentsLink.querySelector('span.hidden')
    expect(labelSpan).not.toBeNull()
    expect(labelSpan).toHaveTextContent('Documents')

    const auditLink = screen.getByRole('link', { name: 'Audit' });
    const auditLabel = auditLink.querySelector('span.hidden')
    expect(auditLabel).not.toBeNull()
    expect(auditLabel).toHaveTextContent('Audit')
  })

  it('threads arbitrary email + role props through to the footer', () => {
    render(<Sidebar userEmail="alice@corp.com" userRoles={['admin']} />)

    // The footer renders whatever was passed — not a hardcoded fixture.
    expect(screen.getByText('alice@corp.com')).toBeInTheDocument()
    expect(screen.getByText('admin')).toBeInTheDocument()

    // Initials are derived from the email ("al" from "alice@").
    expect(screen.getByText('al')).toBeInTheDocument()
  })
})
import { act, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Sidebar } from '../sidebar';

/**
 * Smoke tests for the App Shell rail: the six destinations render, the
 * brand renders, and the 1280px collapse/expand behavior works in both
 * directions. Component-level only — routing integration is 9B/9C scope.
 */

// usePathname throws outside a running Next app; the Sidebar reads it only
// to mark the active item, so stub it to a fixed route.
vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
}));

/** Simulate a viewport change and flush React's state update. */
const setViewport = (width: number) => {
  window.innerWidth = width;
  window.dispatchEvent(new Event('resize'));
};

describe('Sidebar', () => {
  it('renders the brand mark and all six navigation destinations', () => {
    // jsdom defaults to innerWidth 1024, which collapses the rail — pin a
    // desktop viewport before the mount effect reads it.
    window.innerWidth = 1920;
    render(<Sidebar />);

    expect(
      screen.getByRole('link', { name: 'DocExtract AI home' }),
    ).toBeInTheDocument();

    const destinations = [
      'Dashboard',
      'Documents',
      'Upload',
      'Review',
      'Exports',
      'Audit',
    ];
    for (const label of destinations) {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument();
    }

    // Active-route logic: the stubbed pathname is /dashboard.
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute(
      'aria-current',
      'page',
    );

    // Session footer (placeholder values until 9B).
    expect(screen.getByText('user@example.com')).toBeInTheDocument();
  });

  it('collapses to the icon-only rail below 1280px', () => {
    window.innerWidth = 1920;
    render(<Sidebar />);

    act(() => setViewport(1024));

    // Visible labels are unmounted; the accessible names survive through
    // aria-label, so icon-only links remain announced to screen readers.
    expect(screen.queryByText('Documents')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Documents' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Audit' })).toBeInTheDocument();
    expect(screen.queryByText('user@example.com')).not.toBeInTheDocument();
  });

  it('expands again at 1280px and above', () => {
    window.innerWidth = 1024;
    render(<Sidebar />);

    // Exactly 1280 is the expand boundary (collapse is strictly below).
    act(() => setViewport(1280));

    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('user@example.com')).toBeInTheDocument();
  });
});

'use client';

import { useEffect } from 'react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';

/**
 * Document detail error boundary — the route segment's failure state.
 *
 * Next.js App Router error.tsx must be a client component and receives
 * the error + reset; `reset` re-renders the segment, which re-runs the
 * data fetch. A 404-shaped error (the document does not exist in this
 * org, or the id is malformed) surfaces a route back to the register
 * instead of a dead end.
 */
export default function DocumentDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface the error for observability (Next's documented pattern:
    // error boundaries report, then render a recovery state).
    console.error('document detail error', error);
  }, [error]);

  return (
    <div className="border border-rule bg-paper p-8 text-center">
      <p className="text-sm text-ink">This document could not be loaded.</p>
      <p className="mt-1 text-xs text-ink-muted">
        It may have been deleted, or it belongs to another organization.
      </p>
      <div className="mt-4 flex items-center justify-center gap-2">
        <Button variant="outline" size="sm" onClick={reset}>
          Try again
        </Button>
        <Button variant="outline" size="sm" asChild>
          <Link href="/documents">Back to documents</Link>
        </Button>
      </div>
    </div>
  );
}
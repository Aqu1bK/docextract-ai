import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Dashboard',
};

/**
 * Placeholder for the Phase 9B documents overview: upload dropzone entry
 * point, extraction queue status, review queue counts.
 */
export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-2">
      <h1 className="text-lg font-semibold text-ink">Dashboard</h1>
      <p className="text-sm text-ink-muted">
        Documents, extraction queues, and review counts arrive with the
        documents module in Phase 9B.
      </p>
    </div>
  );
}

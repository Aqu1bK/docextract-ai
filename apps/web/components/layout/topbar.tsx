'use client';

import { usePathname } from 'next/navigation';
import { ChevronDown } from 'lucide-react';
import { env } from '@/lib/env';

/**
 * 56px (h-14) chrome bar. Left: the current page title — from the `title`
 * prop when a screen wants to override, otherwise derived from the route.
 * Right: persistent Demo indicator (demo mode only) + user menu (9B).
 */

const ROUTE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/documents': 'Documents',
  '/upload': 'Upload',
  '/review': 'Review',
  '/exports': 'Exports',
  '/audit': 'Audit trail',
};

/** Longest matching prefix wins, so /documents/doc_123 → "Documents". */
function titleFromPathname(pathname: string): string {
  const match = Object.keys(ROUTE_TITLES)
    .filter((route) => pathname === route || pathname.startsWith(`${route}/`))
    .sort((a, b) => b.length - a.length)[0];
  return match ? ROUTE_TITLES[match] : 'DocExtract AI';
}

export function Topbar({ title }: { title?: string }) {
  const pathname = usePathname();
  const pageTitle = title ?? titleFromPathname(pathname);
  const demoMode = env.NEXT_PUBLIC_DEMO_MODE === 'true';

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-rule bg-paper px-6">
      {/* Not an <h1>: screens own their document headings; the topbar is chrome. */}
      <div className="text-sm font-semibold text-ink">{pageTitle}</div>

      <div className="flex items-center gap-3">
        {demoMode && (
          <span
            className="border border-accent/30 bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent"
            title="Demo mode is active — see the banner at the top of the page"
          >
            Demo
          </span>
        )}

        {/* User menu — inert placeholder until 9B wires the Supabase session. */}
        <button
          type="button"
          className="flex cursor-pointer items-center gap-2 border border-rule bg-paper px-2 py-1 hover:bg-paper-muted"
          aria-haspopup="menu"
          title="User menu — wired in Phase 9B"
        >
          <span className="flex size-6 items-center justify-center bg-paper-muted text-[10px] font-medium text-ink">
            DE
          </span>
          <ChevronDown className="size-3.5 text-ink-muted" aria-hidden />
        </button>
      </div>
    </header>
  );
}

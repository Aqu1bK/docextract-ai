// docextract-ai/apps/web/components/layout/sidebar.tsx

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { navItems } from '@/components/layout/nav-items';
import { cn } from '@/lib/utils';

/**
 * Sidebar — the product's primary navigation.
 *
 * 240px expanded, 64px icon-only below the 1280px breakpoint: a CSS-only
 * collapse (xl: variants), because a nav that needs JavaScript to choose
 * its width is a nav that flashes. Active state is the accent-colored
 * left edge — not a pill, not a shadow, a hairline that reads as ink
 * underlining the current place in the workflow.
 *
 * Phase 9B: the active item is computed from the real pathname
 * (usePathname — "current" is no longer static), and the footer shows
 * the signed-in user's email + first role, both resolved server-side by
 * the (app) layout and passed down as props.
 */
export interface SidebarProps {
  /** Signed-in user's email (resolved by the (app) layout's session read). */
  userEmail: string;
  /** The user's backend roles (from GET /auth/me), first one displayed. */
  userRoles: string[];
}

/** Two letters for the footer avatar square: "jo" from "jo@example.com". */
function initialsFromEmail(email: string): string {
  if (email.length === 0) return '–';
  const [localPart] = email.split('@');
  return localPart.slice(0, 2).toLowerCase();
}

export function Sidebar({ userEmail, userRoles }: SidebarProps) {
  const pathname = usePathname();

  const items = navItems.map((item) => ({
    ...item,
    current: pathname === item.href || pathname.startsWith(`${item.href}/`),
  }));

  return (
    <aside className="flex h-full w-16 flex-col border-r border-rule bg-paper lg:w-60">
      {/* Wordmark: full name when there is room, square glyph when not. */}
      <div className="flex h-14 items-center gap-3 border-b border-rule px-4">
        <span
          aria-hidden
          className="flex size-8 shrink-0 items-center justify-center bg-ink font-mono text-sm font-medium text-paper"
        >
          Dx
        </span>
        <span className="hidden text-sm font-semibold tracking-tight lg:inline">DocExtract AI</span>
      </div>

      <nav aria-label="Primary" className="flex flex-1 flex-col gap-1 p-2">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            aria-current={item.current ? 'page' : undefined}
            title={item.label}
            className={cn(
              'flex h-9 items-center gap-3 px-3 text-sm transition-colors',
              item.current
                ? 'bg-paper-muted font-medium text-ink [box-shadow:inset_3px_0_0_var(--color-accent)]'
                : 'text-ink-muted hover:bg-paper-muted hover:text-ink',
            )}
          >
            <item.icon className="size-4 shrink-0" />
            <span className="hidden lg:inline">{item.label}</span>
          </Link>
        ))}
      </nav>

      {/* Signed-in user — email + role, resolved before the shell rendered. */}
      <div className="border-t border-rule p-3">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="flex size-8 shrink-0 items-center justify-center border border-rule bg-paper-muted font-mono text-xs font-medium text-ink"
          >
            {initialsFromEmail(userEmail)}
          </span>
          <div className="hidden min-w-0 lg:block">
            <p className="truncate text-xs text-ink" title={userEmail}>
              {userEmail}
            </p>
            <p className="truncate font-mono text-[10px] text-ink-muted">
              {userRoles[0] ?? 'signed-in'}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
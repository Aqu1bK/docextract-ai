'use client';

import { useRouter } from 'next/navigation';
import { ChevronDown } from 'lucide-react';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { signOut } from '@/lib/auth-client';

/**
 * Topbar — the contextual strip above every authenticated page.
 *
 * 56px, hairline bottom border. Left: the current page title (a prop,
 * because the title is route data, not chrome data). Right: the user
 * menu — a Radix DropdownMenu fed from the session facts the (app)
 * layout already resolved server-side (email + roles) — so this
 * component makes zero auth round trips of its own. Sign out clears
 * the Supabase session cookies and lands on /login; router.refresh()
 * re-renders the server tree so no stale shell flashes.
 */
export interface TopbarProps {
  /** Title of the current page, rendered at the bar's left edge. */
  title: string;
  /** Signed-in user's email (from the (app) layout's server-side session). */
  userEmail: string;
  /** The user's backend roles (from GET /auth/me), first one displayed. */
  userRoles: string[];
}

/** Two letters for the avatar square: "jo" from "jo@example.com". */
function initialsFromEmail(email: string): string {
  if (email.length === 0) return '–';
  const [localPart] = email.split('@');
  return localPart.slice(0, 2).toLowerCase();
}

export function Topbar({ title, userEmail, userRoles }: TopbarProps) {
  const router = useRouter();

  /**
   * Sign out, then navigate.
   *
   * The pushed navigation is what the user sees; refresh guarantees the
   * middleware-guarded server tree re-renders against the now-empty
   * session instead of a cached one.
   */
  async function handleSignOut() {
    await signOut();
    router.push('/login');
    router.refresh();
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-rule bg-paper px-6">
      <h2 className="text-sm font-semibold tracking-tight">{title}</h2>

      <DropdownMenu>
        <DropdownMenuTrigger className="flex cursor-pointer items-center gap-2 border border-rule bg-paper px-2 py-1 text-sm text-ink transition-colors hover:bg-paper-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent">
          <span
            aria-hidden
            className="flex size-6 items-center justify-center bg-paper-muted font-mono text-[10px] font-medium text-ink"
          >
            {initialsFromEmail(userEmail)}
          </span>
          <span className="hidden max-w-[14rem] truncate text-xs text-ink-muted sm:inline">
            {userEmail}
          </span>
          <ChevronDown className="size-3.5 text-ink-muted" aria-hidden />
        </DropdownMenuTrigger>

        <DropdownMenuContent align="end">
          <DropdownMenuLabel>
            {userEmail}
            <span className="ml-1 text-ink-muted">· {userRoles[0] ?? 'signed-in'}</span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem
          onClick={() => {
             void handleSignOut();
              }}
             >
            Sign out
             </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}

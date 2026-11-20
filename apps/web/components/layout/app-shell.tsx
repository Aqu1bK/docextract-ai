// docextract-ai/apps/web/components/layout/app-shell.tsx

'use client';

import { usePathname } from 'next/navigation';

import { DemoModeBanner } from '@/components/layout/demo-mode-banner';
import { Sidebar } from '@/components/layout/sidebar';
import { Topbar } from '@/components/layout/topbar';
import { env } from '@/lib/env';

/**
 * AppShell — the frame every authenticated page renders inside.
 *
 * Column structure: banner strip (when demo mode is on), then a row of
 * [Sidebar | main]. The main column carries the Topbar and the page
 * content, which is padded 24px, capped at 1400px, and centered — dense
 * tables (review queue, audit trail) stay readable on wide monitors
 * instead of stretching to the full viewport.
 *
 * The shell is client-side because the sidebar/topbar own interaction
 * state (active-route detection, user menu); the pages inside remain
 * server components wherever possible. The (app) layout resolves the
 * session server-side and passes the user facts (email + roles) down
 * here as props — one auth read feeds the whole frame, and the shell
 * itself never touches Supabase.
 */
const ROUTE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/documents': 'Documents',
  '/upload': 'Upload',
  '/review': 'Review',
  '/exports': 'Exports',
  '/audit': 'Audit trail',
};

/** The topbar title for a pathname: longest matching route prefix wins. */
function titleFromPathname(pathname: string): string {
  const match = Object.keys(ROUTE_TITLES)
    .filter((route) => pathname === route || pathname.startsWith(`${route}/`))
    .sort((a, b) => b.length - a.length)[0];
  return match !== undefined ? ROUTE_TITLES[match] : 'DocExtract AI';
}

export interface AppShellProps {
  /** Signed-in user's email (resolved by the (app) layout's session read). */
  userEmail: string;
  /** The user's backend roles (from GET /auth/me). */
  userRoles: string[];
  children: React.ReactNode;
}

export function AppShell({ userEmail, userRoles, children }: AppShellProps) {
  const pathname = usePathname();
  const title = titleFromPathname(pathname);

  return (
    <div className="flex min-h-screen flex-col">
      {/* The banner always reserves its 32px strip in demo mode so the
          layout never jumps when it appears or collapses. */}
      {env.demoMode ? <DemoModeBanner /> : null}
      <div className="flex flex-1">
        <Sidebar userEmail={userEmail} userRoles={userRoles} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar title={title} userEmail={userEmail} userRoles={userRoles} />
          <main className="flex-1">
            <div className="mx-auto w-full max-w-[1400px] px-6 py-6">{children}</div>
          </main>
        </div>
      </div>
    </div>
  );
}
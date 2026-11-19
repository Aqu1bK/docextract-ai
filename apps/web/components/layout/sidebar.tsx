'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  ClipboardCheck,
  Download,
  FileScan,
  FileText,
  LayoutDashboard,
  ScrollText,
  Upload,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Fixed 240px rail (w-60); collapses to a 64px icon rail (w-16) below
 * 1280px via a resize listener. Icon-only items keep their label through
 * `title` + `aria-label` — no tooltip dependency needed in Phase 9A.
 *
 * Destinations are placeholders until 9B/9C create the routes; only
 * /dashboard exists today.
 */
const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/documents', label: 'Documents', icon: FileText },
  { href: '/upload', label: 'Upload', icon: Upload },
  { href: '/review', label: 'Review', icon: ClipboardCheck },
  { href: '/exports', label: 'Exports', icon: Download },
  { href: '/audit', label: 'Audit', icon: ScrollText },
] as const;

const COLLAPSE_BELOW = 1280;

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const update = () => setCollapsed(window.innerWidth < COLLAPSE_BELOW);
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  return (
    <aside
      className={cn(
        'flex h-full shrink-0 flex-col border-r border-rule bg-paper',
        collapsed ? 'w-16' : 'w-60',
      )}
      aria-label="Primary"
    >
      {/* Brand — the "AI" is set in the mono face: the machine part of the
          product name, typeset like the machine data it refers to. */}
      <Link
        href="/dashboard"
        className="flex h-14 items-center gap-2.5 border-b border-rule px-4"
        aria-label="DocExtract AI home"
      >
        <FileScan className="size-5 shrink-0 text-ink" aria-hidden />
        {!collapsed && (
          <span className="text-sm font-semibold tracking-tight text-ink">
            DocExtract <span className="font-mono font-medium">AI</span>
          </span>
        )}
      </Link>

      {/* Primary navigation. Inactive items carry a 2px transparent left
          border so activating an item never shifts the label 2px. */}
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2">
        {NAV_ITEMS.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              aria-label={collapsed ? item.label : undefined}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'flex items-center gap-3 border-l-2 px-3 py-2 text-sm',
                collapsed && 'justify-center px-0',
                active
                  ? 'border-accent bg-paper-muted font-medium text-ink'
                  : 'border-transparent text-ink-muted hover:bg-paper-muted/60 hover:text-ink',
              )}
            >
              <Icon className="size-4 shrink-0" aria-hidden />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Session — placeholder values until 9B wires the Supabase user. */}
      <div className="border-t border-rule p-3">
        <div
          className={cn(
            'flex items-center gap-2.5',
            collapsed && 'justify-center',
          )}
        >
          <div className="flex size-8 shrink-0 items-center justify-center border border-rule bg-paper-muted text-xs font-medium text-ink">
            DE
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate text-xs text-ink">user@example.com</p>
              <p className="text-xs text-ink-muted">Recruiter</p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

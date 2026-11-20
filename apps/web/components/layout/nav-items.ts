// docextract-ai/apps/web/components/layout/nav-items.ts

import {
  ClipboardCheck,
  Download,
  FileText,
  LayoutDashboard,
  ScrollText,
  Upload,
  type LucideIcon,
} from 'lucide-react';

/**
 * The application-wide nav definition.
 *
 * One entry per top-level product area. 9C lands the review surface at
 * /documents/{id}: a reviewer's day starts at the Documents register,
 * so "Review" points there — the register row's destination IS the
 * review screen. The Exports and Audit items keep their hrefs for the
 * cross-document screens of a later phase; a dedicated review route is
 * out of scope for 9C, so this is the real wiring, not a placeholder.
 * `current` is computed by the sidebar from the active pathname (9B).
 */
export interface NavItem {
  /** Route the item points at. */
  href: string;
  /** Sidebar label (hidden at the 64px collapsed width). */
  label: string;
  /** lucide-react icon shown in both expanded and collapsed states. */
  icon: LucideIcon;
  /** Whether this item is the active route. */
  current: boolean;
}

export const navItems: NavItem[] = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, current: true },
  { href: '/documents', label: 'Documents', icon: FileText, current: false },
  { href: '/upload', label: 'Upload', icon: Upload, current: false },
  { href: '/documents', label: 'Review', icon: ClipboardCheck, current: false },
  { href: '/exports', label: 'Exports', icon: Download, current: false },
  { href: '/audit', label: 'Audit', icon: ScrollText, current: false },
];
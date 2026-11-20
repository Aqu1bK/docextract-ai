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
 * The product's primary navigation destinations, defined once and
 * consumed by the Sidebar. A nav item is the minimum shape the Sidebar
 * needs: a route, a human label, and an icon component.
 *
 * Adding a new destination = one entry here. The Sidebar renders
 * whatever this array contains, so the nav grows with the product
 * without any per-file changes.
 */
export interface NavItem {
  /** Route path, e.g. "/dashboard". */
  href: string;
  /** Visible label (and tooltip when collapsed). */
  label: string;
  /** Lucide icon component. */
  icon: LucideIcon;
}

export const navItems: NavItem[] = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/documents', label: 'Documents', icon: FileText },
  { href: '/upload', label: 'Upload', icon: Upload },
  { href: '/review', label: 'Review', icon: ClipboardCheck },
  { href: '/exports', label: 'Exports', icon: Download },
  { href: '/audit', label: 'Audit trail', icon: ScrollText },
];
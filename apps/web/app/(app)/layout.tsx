import { AppShell } from '@/components/layout/app-shell';

/**
 * Layout for every authenticated screen. Route groups carry no URL
 * segment: (app) pages live at /dashboard, /documents, ... while the
 * (auth) group stays outside this frame.
 */
export default function AppGroupLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <AppShell>{children}</AppShell>;
}

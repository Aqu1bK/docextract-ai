import { AppShell } from '@/components/layout/app-shell';
import { fetchCurrentUserRoles, requireUser } from '@/lib/auth';

/**
 * Authenticated-app layout — the auth guard plus the shell.
 *
 * Two server-side reads happen before any shell byte renders:
 * `requireUser()` (redirect anonymous → /login — the layout-level guard;
 * middleware already checked, this is the belt to its suspenders), and
 * `fetchCurrentUserRoles()` (GET /auth/me — the backend's answer for
 * "what roles does this JWT hold?"), which the sidebar footer and topbar
 * user menu display. Passing user facts down as props keeps every page
 * under (app) free of auth logic: they render inside a shell that
 * already knows who is signed in.
 */
export default async function AppGroupLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser();
  const roles = await fetchCurrentUserRoles();

  return (
    <AppShell
      userEmail={user.email ?? ''}
      userRoles={roles.length > 0 ? roles : ['signed-in']}
    >
      {children}
    </AppShell>
  );
}
import { redirect } from 'next/navigation';

import { getCurrentUser } from '@/lib/auth';

/**
 * Root route — the front door that sorts visitors.
 *
 * Signed in → /dashboard (the shell renders immediately; the middleware
 * has already refreshed the session on the way in). Signed out → /login.
 * The check is server-side via auth.getUser(), so an expired session
 * never flashes the app shell before the redirect lands.
 */
export default async function RootPage() {
  const user = await getCurrentUser();
  redirect(user !== null ? '/dashboard' : '/login');
}
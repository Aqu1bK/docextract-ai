import { redirect } from 'next/navigation';

/**
 * The root route owns no screen. The only entry point for a visitor is
 * the sign-in page — 9A redirects unconditionally; 9B replaces this with
 * an auth-state check (signed in → /dashboard, signed out → /login).
 */
export default function RootPage() {
  redirect('/login');
}

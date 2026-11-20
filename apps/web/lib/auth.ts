import { redirect } from 'next/navigation';

import { env } from './env';
import { createSupabaseServerClient } from './supabase-server';

/**
 * Auth helpers — the server-side half of the session boundary.
 *
 * Login is a browser concern (lib/auth-client.ts calls Supabase
 * signInWithPassword from the form component); this module answers the
 * two questions server code asks instead: "who is the current user?"
 * (getCurrentUser) and "is anyone signed in at all?" (requireUser).
 *
 * `auth.getUser()` — not `getSession()` — is the verifier here: it
 * revalidates the JWT with Supabase on every call, while `getSession()`
 * only reads the stored token without checking it. The official
 * @supabase/ssr docs use getUser() in middleware and layouts precisely
 * because a middleware check that trusts an unverified token is no check.
 */

/** Shape returned by /auth/me — the backend's identity + roles answer. */
export interface BackendMe {
  user_id: string;
  email: string;
  full_name: string | null;
  roles: string[];
}

/**
 * The signed-in user, or null when the session is absent/invalid.
 *
 * Returns the Supabase `User` (id + email); roles live in the backend
 * database, so pair this with fetchCurrentUserRoles when a surface needs
 * "Admin" rather than "signed in".
 */
export async function getCurrentUser() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return user;
}

/**
 * The current user's roles from the backend (GET /auth/me).
 *
 * Called from server components only: the access token travels once,
 * server-to-server, and never reaches the browser bundle.
 */
export async function fetchCurrentUserRoles(): Promise<string[]> {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (session === null) return [];

  const response = await fetch(`${env.apiBaseUrl}/auth/me`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
    cache: 'no-store',
  });
  if (!response.ok) return [];

  const me = (await response.json()) as BackendMe;
  return me.roles;
}

/**
 * Navigation guard for (app) layouts: redirect anonymous visitors to the
 * login page instead of rendering a shell that has no user to show.
 */
export async function requireUser() {
  const user = await getCurrentUser();
  if (user === null) redirect('/login');

  return user;
}
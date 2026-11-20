import { createClient } from './supabase-browser';

/**
 * Browser-side auth actions — the form's vocabulary.
 *
 * These run only in client components (the login form, the topbar sign-out
 * button): they drive Supabase's browser client, which writes the session
 * cookies that the rest of the app (middleware, layouts, API client) reads.
 * `signInWithPassword` is used rather than `signInWithOAuth` because the
 * demo accounts are pre-created email/password users — there is no OAuth
 * provider to bounce through, and the seeded demo credentials pair exactly
 * with this flow.
 */

/**
 * One seeded demo account. The login form renders these as clickable
 * cards: `id` is the React key, `label` is the visible name ("Admin"),
 * `roleSummary` is the one-line explanation shown under the button.
 *
 * PATCH NOTE (Phase 9B reconciliation): the Chunk 2 login-form.tsx
 * expects these fields; Chunk 1 only had role/email/password.
 */
export interface DemoAccount {
  id: string;
  label: string;
  email: string;
  password: string;
  roleSummary: string;
}

/** Credentials for the four seeded demo accounts (README "Live Demo"). */
export const DEMO_ACCOUNTS: readonly DemoAccount[] = [
  {
    id: 'admin',
    label: 'Admin',
    email: 'admin@demo.docextract.ai',
    password: 'DemoAdmin123!',
    roleSummary: 'Manages users and system settings',
  },
  {
    id: 'reviewer',
    label: 'Reviewer',
    email: 'reviewer@demo.docextract.ai',
    password: 'DemoReviewer123!',
    roleSummary: 'Reviews and approves extractions',
  },
  {
    id: 'uploader',
    label: 'Uploader',
    email: 'uploader@demo.docextract.ai',
    password: 'DemoUploader123!',
    roleSummary: 'Uploads documents for extraction',
  },
  {
    id: 'viewer',
    label: 'Viewer',
    email: 'viewer@demo.docextract.ai',
    password: 'DemoViewer123!',
    roleSummary: 'Reads approved documents and exports',
  },
] as const;

/**
 * Sign in with email + password via Supabase Auth.
 *
 * Returns Supabase's AuthResponse; the login form reads `error` to toast
 * and `data.user` to navigate to /dashboard on success.
 */
export async function signInWithPassword(email: string, password: string) {
  const supabase = createClient();
  return supabase.auth.signInWithPassword({ email, password });
}

/** Sign out and clear the session cookies. */
export async function signOut() {
  const supabase = createClient();
  return supabase.auth.signOut();
}

/**
 * The signed-in user (id + email) as the browser sees it, or null.
 *
 * `getUser()` revalidates the token with Supabase rather than trusting
 * the cookie contents (see lib/auth.ts for why that distinction matters).
 */
export async function getUser() {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return user;
}
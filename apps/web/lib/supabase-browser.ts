import { createBrowserClient } from '@supabase/ssr';

import { env } from './env';

/**
 * Browser Supabase client — the ONLY client that touches cookies from
 * the tab's side.
 *
 * `createBrowserClient` (the @supabase/ssr factory) stores the session
 * in cookies instead of localStorage, so the same session is visible to
 * the server, the middleware, and the browser tab. It is a singleton by
 * design: supabase-js warns ("Multiple GoTrueClient instances") if a
 * page renders more than one browser client, and the cheapest guard is
 * to cache the instance module-wide. One instance means one auth state
 * change stream.
 *
 * This module is deliberately separate from lib/supabase-server.ts:
 * importing `next/headers` here would break every client bundle that
 * transitively pulls this file (Next's build fails the build, not the
 * page). Client components only; server code uses
 * createSupabaseServerClient().
 */
let browserClient: ReturnType<typeof createBrowserClient> | null = null;

/**
 * The browser-side Supabase client, created lazily and cached.
 *
 * Lazy + cached (rather than top-level) because module load order is
 * not ours to control in tests: importing this module must not
 * construct a client before the environment is mocked.
 */
export function createClient(): ReturnType<typeof createBrowserClient> {
  if (browserClient === null) {
    browserClient = createBrowserClient(env.supabaseUrl, env.supabaseAnonKey);
  }
  return browserClient;
}
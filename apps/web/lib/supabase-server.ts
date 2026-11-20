import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

import { env } from './env';

/**
 * Server Supabase client for Server Components, route handlers, and
 * Server Actions — every context where `cookies()` is available.
 *
 * Cookie adapter: `getAll` reads the request cookies; `setAll` writes
 * refreshed session cookies. The write is wrapped in try/catch because a
 * Server Component render is not allowed to set cookies — the refresh
 * then happens in middleware instead, which can. That fallback ordering
 * is the documented @supabase/ssr pattern.
 *
 * This module is deliberately separate from lib/supabase-browser.ts:
 * `next/headers` must never be importable from the client half of the
 * graph (Next fails the build if a client bundle reaches it), so server
 * code imports THIS file and client code imports that one. The middleware
 * builds its own client with raw `process.env` reads instead — see
 * middleware.ts for why.
 *
 * PATCH NOTE (Phase 9B reconciliation): the Chunk 2 auth callback route
 * imports this as `getSupabaseServerClient` (a more accurate name — it
 * *gets* an existing client bound to the current request, not creates a
 * fresh one). Export alias kept for backward compat.
 */
export async function getSupabaseServerClient(): Promise<
  ReturnType<typeof createServerClient>
> {
  const cookieStore = await cookies();

  return createServerClient(env.supabaseUrl, env.supabaseAnonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options);
          });
        } catch {
          // Called from a Server Component: middleware refreshed the
          // session instead, so this write is expected to fail.
        }
      },
    },
  });
}

/** Back-compat alias for the Chunk 1 auth helpers that used the old name. */
export const createSupabaseServerClient = getSupabaseServerClient;
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

import { getSupabaseServerClient } from '@/lib/supabase-server'

/**
 * Auth callback: `GET /auth/callback`
 *
 * Supabase Auth emails (magic link, email confirmation, password recovery)
 * use the PKCE flow and land here as `/auth/callback?code=<one-time-code>`.
 * This handler exchanges that code for a session. The @supabase/ssr cookie
 * adapter inside `getSupabaseServerClient()` (see `lib/supabase-server.ts`)
 * writes the session cookies onto this very response, so the redirect target
 * renders authenticated on its first request — no client-side round-trip.
 *
 * Notes:
 * - `exchangeCodeForSession` is single-use. Refreshing this URL after a
 *   successful exchange finds a consumed code and falls through to the
 *   failure redirect, which is the correct outcome for a consumed link.
 * - Route handlers are the only server context (besides middleware) that can
 *   carry `Set-Cookie` from the Supabase adapter via `NextResponse`.
 */

/** Fallback redirect target when the email link carries no `next` param. */
const DEFAULT_REDIRECT = '/dashboard'

/**
 * Login redirect used for every failure mode (missing / expired / already
 * consumed code). The login form reads `error=auth_callback` from the URL
 * and surfaces it as a toast.
 */
const LOGIN_FAILURE_URL = '/login?error=auth_callback'

/**
 * Resolve the absolute origin for redirects.
 *
 * `request.nextUrl.origin` is correct for local development. Behind a
 * reverse proxy the public host can differ from the internal one, so the
 * proxy's `x-forwarded-host` header wins when present.
 */
function resolveOrigin(request: NextRequest): string {
  const forwardedHost = request.headers.get('x-forwarded-host')
  if (forwardedHost) {
    return `https://${forwardedHost}`
  }
  return request.nextUrl.origin
}

/**
 * Allow only same-origin relative paths as post-login redirect targets.
 * Absolute URLs and protocol-relative URLs (`//example.com`) are rejected —
 * otherwise the callback would become an open redirect.
 */
function sanitizeNextPath(value: string | null): string {
  if (value && value.startsWith('/') && !value.startsWith('//')) {
    return value
  }
  return DEFAULT_REDIRECT
}

/**
 * Exchange the one-time auth code for a session.
 *
 * Success -> 302 to the sanitized `next` path (default `/dashboard`).
 * Failure -> 302 to `/login?error=auth_callback`.
 */
export async function GET(request: NextRequest): Promise<NextResponse> {
  const { searchParams } = request.nextUrl
  const code = searchParams.get('code')
  const next = sanitizeNextPath(searchParams.get('next'))

  if (code) {
    const supabase = await getSupabaseServerClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)

    if (!error) {
      return NextResponse.redirect(new URL(next, resolveOrigin(request)))
    }

    // Non-null error means the code was expired or already consumed.
    // Log the reason server-side only; the user gets a neutral toast.
    console.error('[auth/callback] code exchange failed:', error.message)
  }

  return NextResponse.redirect(new URL(LOGIN_FAILURE_URL, resolveOrigin(request)))
}
import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

/**
 * Middleware — the session's first stop on every request.
 *
 * Two jobs, in this order:
 * 1. Refresh the session: expired access tokens are exchanged for fresh
 *    ones here, and the new cookies ride back on `supabaseResponse`. This
 *    is why the response object must be returned (not a bare
 *    NextResponse.next()) — the refreshed cookies would otherwise be
 *    dropped, and every subsequent request would re-expire.
 * 2. Guard the (app) routes: an anonymous request for /dashboard,
 *    /documents, /upload, /review, /exports, /audit is redirected to
 *    /login before any server component renders.
 *
 * Verification uses `auth.getUser()` — the call that revalidates the
 * token with the Supabase server — rather than `auth.getSession()`,
 * which trusts whatever the cookie says. The matcher excludes static
 * assets so it runs exactly once per page/document request.
 *
 * Route list is explicit (not a "/dashboard" prefix test): (app) contains
 * six top-level areas, and an explicit list reads as the product's map.
 */
const PROTECTED_ROUTES = [
  '/dashboard',
  '/documents',
  '/upload',
  '/review',
  '/exports',
  '/audit',
];

export async function proxy(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => {
            request.cookies.set(name, value);
          });
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) => {
            supabaseResponse.cookies.set(name, value, options);
          });
        },
      },
    },
  );

  // getUser() (not getSession()): the token is revalidated with Supabase
  // before any route decision is made from it.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const isProtected = PROTECTED_ROUTES.some(
    (route) => request.nextUrl.pathname === route || request.nextUrl.pathname.startsWith(`${route}/`),
  );

  if (!user && isProtected) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
};
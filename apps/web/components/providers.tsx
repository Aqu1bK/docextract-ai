'use client'

import { QueryClient, QueryClientProvider, isServer } from '@tanstack/react-query'
import type { ReactNode } from 'react'

/**
 * Build a QueryClient with the app-wide defaults.
 *
 * A one-minute `staleTime` keeps server-rendered data from refetching
 * immediately after hydration. Everything else stays on TanStack Query v5
 * defaults (3 retries, refetch on window focus) — change per-route when a
 * route needs different behavior, not globally here.
 */
function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
      },
    },
  })
}

/**
 * Browser-side singleton. Kept at module scope (not in useState) so a
 * suspended initial render can never produce two clients.
 */
let browserQueryClient: QueryClient | undefined

function getQueryClient(): QueryClient {
  if (isServer) {
    // Server: a fresh client per call. A shared client here would leak
    // cache and state across requests — and across users.
    return makeQueryClient()
  }

  // Browser: create the singleton on first use, then reuse it.
  if (browserQueryClient === undefined) {
    browserQueryClient = makeQueryClient()
  }
  return browserQueryClient
}

/**
 * Global client providers — mounted exactly once in `app/layout.tsx`,
 * wrapping `{children}` inside `<body>` (Phase 9B wiring).
 *
 * Keeping every provider in one component lets the root layout stay
 * server-only: it can render fonts and the static theme markup without
 * becoming a client component itself.
 *
 * Devtools are deliberately not bundled; add `@tanstack/react-query-devtools`
 * behind a dev-only check here if inspection is ever needed.
 */
export function Providers({ children }: { children: ReactNode }) {
  const queryClient = getQueryClient()

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}
import type { Metadata } from 'next'
import Link from 'next/link'

import { DocumentsView } from '@/components/documents/documents-view'
import { buttonVariants } from '@/components/ui/button'
import { requireUser } from '@/lib/auth'
import { cn } from '@/lib/utils'

export const metadata: Metadata = {
  title: 'Documents',
  description: 'Browse every uploaded document with its extraction status and review progress.',
}

/**
 * Documents — server wrapper for the documents list.
 *
 * Phase 9B page contract: the server component owns authentication,
 * metadata, and the page chrome (eyebrow / title / primary action); the
 * interactive register itself is the client boundary (`DocumentsView`),
 * which loads data through `useDocuments()` from `lib/queries.ts` so list
 * state (filters, pagination) survives navigation.
 *
 * `requireUser()` makes this route's auth requirement explicit. Middleware
 * already refreshed the session and redirected anonymous visitors, so this
 * call is a cheap per-route guarantee rather than the first line of defense.
 */
export default async function DocumentsPage() {
  await requireUser()

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-8 sm:px-6 lg:px-10">
      <header className="flex flex-col gap-4 border-b border-rule pb-6 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-1">
          {/* Eyebrow — JetBrains Mono marks structural / machine labels. */}
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/50">
            Workspace
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Documents</h1>
          <p className="max-w-prose text-sm leading-relaxed text-ink/60">
            Every upload with its extraction status and review progress, newest first.
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          {/*
            `buttonVariants` + Link is the Phase 9A replacement for the
            shadcn `asChild` pattern (no Radix Slot dependency).
          */}
          <Link href="/upload" className={cn(buttonVariants(), 'whitespace-nowrap')}>
            Upload document
          </Link>
        </div>
      </header>

      {/*
        Client boundary. `DocumentsView` owns the table, empty state, and
        loading state; all data fetching happens inside it via TanStack Query.
      */}
      <DocumentsView />
    </div>
  )
}
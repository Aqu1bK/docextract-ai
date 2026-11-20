'use client'

import { useMutation } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import type { FormEvent } from 'react'

import { buttonVariants } from '@/components/ui/button'
import { DEMO_ACCOUNTS, signInWithPassword } from '@/lib/auth-client'
import type { DemoAccount } from '@/lib/auth-client'
import { env } from '@/lib/env'
import { cn } from '@/lib/utils'

/** Where to send the user after sign-in when no `next` param exists. */
const DEFAULT_REDIRECT = '/dashboard'

/**
 * Message shown when `/auth/callback` bounced back here because the email
 * link was expired or already consumed
 * (see `app/(auth)/auth/callback/route.ts`).
 */
const AUTH_CALLBACK_FAILED_MESSAGE =
  'That sign-in link has expired or was already used. Sign in with your credentials instead.'

/** Shape passed into the sign-in mutation from both the form and the demo buttons. */
interface SignInCredentials {
  email: string
  password: string
}

/**
 * Login-page context carried on the URL by earlier steps of the auth flow:
 * - `authError` — the email-link code exchange failed (`?error=auth_callback`)
 * - `nextPath` — the route middleware saved before redirecting to `/login`
 */
interface LoginContext {
  authError: string | null
  nextPath: string | null
}

/**
 * Read the login context from the URL once, on mount.
 *
 * Deliberately uses `window.location.search` instead of `useSearchParams()`:
 * that hook forces a Suspense boundary around any component that uses it on
 * a statically rendered page, and the login page is static. Reading the raw
 * `window.location` inside `useEffect` avoids that constraint (and any
 * hydration mismatch — the server render never sees these values).
 */
function readLoginContext(): LoginContext {
  const params = new URLSearchParams(window.location.search)
  const nextPath = params.get('next')

  return {
    authError: params.get('error') === 'auth_callback' ? AUTH_CALLBACK_FAILED_MESSAGE : null,
    // Same-origin relative paths only — mirrors the sanitizer in the auth
    // callback route and keeps post-login navigation from becoming an
    // open redirect.
    nextPath:
      nextPath && nextPath.startsWith('/') && !nextPath.startsWith('//') ? nextPath : null,
  }
}

/**
 * Login form — credentials + one-click demo accounts.
 *
 * Sign-in goes through the browser auth vocabulary in `lib/auth-client.ts`
 * (`signInWithPassword`), which drives the @supabase/ssr browser client and
 * therefore writes the session cookies onto the document directly. On
 * success all that is left to do is navigate: the replaced route reads the
 * fresh cookies server-side on its first render.
 *
 * Failures (wrong password, unconfirmed email, network) surface in a
 * fixed-position toast at the bottom of the viewport — no animation, just a
 * hairline-bordered panel with a mono `error` prefix, per Ink on Paper.
 */
export function LoginForm() {
  const router = useRouter()
  const [loginContext, setLoginContext] = useState<LoginContext>(() =>
  typeof window !== 'undefined' ? readLoginContext() : { authError: null, nextPath: null },
)


  const signInMutation = useMutation({
    mutationFn: ({ email, password }: SignInCredentials) => signInWithPassword(email, password),
    onSuccess: () => {
      const target = loginContext.nextPath ?? DEFAULT_REDIRECT
      // Session cookies were written by @supabase/ssr during the mutation,
      // so this navigation request is already authenticated.
      router.replace(target)
      // Belt-and-braces: refresh any still-mounted server components that
      // rendered the anonymous shell.
      router.refresh()
    },
  })

  /** Email of the in-flight sign-in, used to badge the pending demo button. */
  const pendingEmail = signInMutation.isPending ? signInMutation.variables?.email ?? null : null

  /** Whatever error should currently occupy the toast, if any. */
  const visibleError =
    loginContext.authError ?? (signInMutation.isError ? signInMutation.error.message : null)

  /**
   * Demo affordances compile in but render only in demo mode — the same
   * `NEXT_PUBLIC_DEMO_MODE` gate as `<DemoModeBanner />`, so a production
   * login screen never advertises seeded credentials.
   */
  const showDemoAccounts = env.NEXT_PUBLIC_DEMO_MODE === 'true'

  function clearStaleAuthError() {
    // A new attempt invalidates whatever the callback route complained about.
    if (loginContext.authError) {
      setLoginContext((context) => ({ ...context, authError: null }))
    }
  }

  function handleCredentialsSubmit(event: FormEvent<HTMLFormElement>) {
    // Uncontrolled fields read through FormData: no per-keystroke state.
    // Native `required` already gates submission in the browser; the guard
    // below only covers programmatic submits.
    event.preventDefault()
    clearStaleAuthError()

    const formData = new FormData(event.currentTarget)
    const email = String(formData.get('email') ?? '').trim()
    const password = String(formData.get('password') ?? '')

    if (!email || !password) {
      return
    }

    signInMutation.mutate({ email, password })
  }

  function handleDemoAccountSignIn(account: DemoAccount) {
    // One click = the demo account's seeded credentials. No prefill step;
    // the point is the shortest path to a role-specific session. Shipping
    // these passwords to the client is acceptable because demo accounts
    // exist only for local/demo runs, never in production.
    clearStaleAuthError()
    signInMutation.mutate({ email: account.email, password: account.password })
  }

  function handleDismissError() {
    signInMutation.reset()
    setLoginContext((context) => ({ ...context, authError: null }))
  }

  return (
    <div className="w-full max-w-md">
      <div className="border border-rule bg-paper px-6 py-8 sm:px-8">
        <div className="flex flex-col gap-1.5">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/50">
            DocExtract AI
          </p>
          <h1 className="text-xl font-semibold tracking-tight text-ink">Sign in</h1>
          <p className="text-sm leading-relaxed text-ink/60">
            {showDemoAccounts
              ? 'Use your workspace credentials, or pick a demo account to explore the platform.'
              : 'Use your workspace credentials to continue.'}
          </p>
        </div>

        <form onSubmit={handleCredentialsSubmit} className="mt-6 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="login-email"
              className="text-xs font-medium uppercase tracking-wide text-ink/70"
            >
              Email
            </label>
            {/*
              Inputs are hand-rolled (Phase 9A ships no <Input> component on
              purpose: zero Radix). Keyboard focus comes from the global
              :focus-visible rule in globals.css, so no local focus utilities
              are needed.
            */}
            <input
              id="login-email"
              name="email"
              type="email"
              autoComplete="email"
              required
              spellCheck={false}
              className="h-10 w-full border border-rule bg-paper px-3 text-sm text-ink placeholder:text-ink/40"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="login-password"
              className="text-xs font-medium uppercase tracking-wide text-ink/70"
            >
              Password
            </label>
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              className="h-10 w-full border border-rule bg-paper px-3 text-sm text-ink placeholder:text-ink/40"
            />
          </div>

          <button
            type="submit"
            disabled={signInMutation.isPending}
            aria-busy={signInMutation.isPending}
            className={cn(buttonVariants(), 'h-10 w-full')}
          >
            {signInMutation.isPending ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        {showDemoAccounts ? (
          <section aria-label="Demo accounts" className="mt-8">
            <div className="flex items-center gap-3" aria-hidden="true">
              <span className="h-px flex-1 bg-rule" />
              <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/50">
                Demo accounts
              </span>
              <span className="h-px flex-1 bg-rule" />
            </div>

            <p className="mt-3 text-xs leading-relaxed text-ink/50">
              Seeded local accounts — one click signs in with the credentials for that role.
            </p>

            <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
              {DEMO_ACCOUNTS.map((account) => {
                const isPendingAccount = pendingEmail === account.email

                return (
                  <button
                    key={account.id}
                    type="button"
                    onClick={() => handleDemoAccountSignIn(account)}
                    disabled={signInMutation.isPending}
                    aria-busy={isPendingAccount}
                    className="flex min-h-16 flex-col items-start justify-center gap-1 border border-rule bg-paper px-3 py-2.5 text-left hover:border-ink disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <span className="text-sm font-medium text-ink">{account.label}</span>
                    <span className="w-full truncate font-mono text-[11px] text-ink/50">
                      {account.email}
                    </span>
                    {isPendingAccount ? (
                      <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/50">
                        Signing in…
                      </span>
                    ) : null}
                  </button>
                )
              })}
            </div>
          </section>
        ) : null}
      </div>

      {/*
        Error toast. Mounts only when there is something to say; `role="alert"`
        announces it on mount, and both a manual dismiss and any new sign-in
        attempt clear it. No animation — it simply appears and disappears.
      */}
      {visibleError ? (
        <div
          role="alert"
          className="fixed inset-x-4 bottom-4 z-50 flex items-start justify-between gap-4 border border-ink bg-paper px-4 py-3 sm:inset-x-auto sm:bottom-6 sm:right-6 sm:w-96"
        >
          <div className="flex min-w-0 flex-col gap-1">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink/50">
              error
            </span>
            <p className="text-sm leading-relaxed text-ink">{visibleError}</p>
          </div>
          <button
            type="button"
            onClick={handleDismissError}
            aria-label="Dismiss error"
            className="shrink-0 p-1 text-ink/60 hover:text-ink"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              aria-hidden="true"
              className="h-4 w-4"
            >
              <path d="M4 4l8 8M12 4l-8 8" />
            </svg>
          </button>
        </div>
      ) : null}
    </div>
  )
}
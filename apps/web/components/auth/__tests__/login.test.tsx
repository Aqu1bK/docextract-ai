import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LoginForm } from '@/components/auth/login-form'
import { signInWithPassword } from '@/lib/auth-client'

/**
 * LoginForm — smoke tests.
 *
 * Mocked at the seams, real everywhere else:
 * - `next/navigation`    — the form only navigates; no router to stand up.
 * - `@/lib/env`          — the real module fail-fasts (zod) against
 *                          process.env at import time, which tests do not
 *                          provide. 'true' turns the demo gate on.
 * - `@/lib/auth-client`  — sign-in is faked; DEMO_ACCOUNTS is a fixed
 *                          four-account fixture shared with assertions via
 *                          vi.hoisted (mock factories are hoisted above
 *                          imports, so plain module-scope constants are not
 *                          visible inside them).
 *
 * TanStack Query runs REAL: useMutation needs a provider, and the smoke
 * value here is the wiring (fields -> mutate -> toast), not the mutation
 * engine.
 */

const { mockDemoAccounts } = vi.hoisted(() => ({
  mockDemoAccounts: [
    {
      id: 'admin',
      label: 'Admin',
      email: 'admin@demo.docextract.ai',
      password: 'Demo1234!',
      roleSummary: 'Full platform access',
    },
    {
      id: 'reviewer',
      label: 'Reviewer',
      email: 'reviewer@demo.docextract.ai',
      password: 'Demo1234!',
      roleSummary: 'Review queue access',
    },
    {
      id: 'extractor',
      label: 'Extractor',
      email: 'extractor@demo.docextract.ai',
      password: 'Demo1234!',
      roleSummary: 'Intake access',
    },
    {
      id: 'viewer',
      label: 'Viewer',
      email: 'viewer@demo.docextract.ai',
      password: 'Demo1234!',
      roleSummary: 'Read-only access',
    },
  ],
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    replace: vi.fn(),
    refresh: vi.fn(),
  }),
}))

vi.mock('@/lib/env', () => ({
  env: {
    // Demo affordances render only when the gate reads 'true'.
    NEXT_PUBLIC_DEMO_MODE: 'true',
  },
}))

vi.mock('@/lib/auth-client', () => ({
  signInWithPassword: vi.fn(),
  DEMO_ACCOUNTS: mockDemoAccounts,
}))

/**
 * Fresh client per render with retries OFF.
 *
 * This is load-bearing: with TanStack Query's default policy a rejected
 * mutation retries three times with backoff, and the error state would
 * not surface until the fourth failure — far past waitFor's default
 * timeout. A smoke test wants the first rejection, immediately.
 */
function renderLoginForm() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <LoginForm />
    </QueryClientProvider>
  )
}

beforeEach(() => {
  // Clears call history (signInWithPassword) without touching the
  // DEMO_ACCOUNTS fixture data or module-level mock implementations.
  vi.clearAllMocks()
})

describe('LoginForm', () => {
  it('renders the sign-in card with credential fields and a submit button', () => {
    renderLoginForm()

    expect(screen.getByRole('heading', { level: 1, name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('renders one demo sign-in button per seeded demo account', () => {
    renderLoginForm()

    // The demo section is a named <section>, i.e. a landmark region.
    const demoSection = screen.getByRole('region', { name: 'Demo accounts' })
    const demoButtons = within(demoSection).getAllByRole('button')

    expect(demoButtons).toHaveLength(mockDemoAccounts.length)

    // Each button is nameable by its account's machine identity (the
    // mono email line is part of the accessible name).
    for (const account of mockDemoAccounts) {
      // Use the role label as the query anchor — it's unique per account
      // and avoids the substring-match trap where "viewer" would match
      // inside "reviewer" with an email-regex.
      const button = within(demoSection).getByRole('button', {
        name: new RegExp(`^${account.label}\\b`),
      })
      expect(button).toBeEnabled()
      // Verify the email is actually rendered on that button.
      expect(button).toHaveTextContent(account.email)
    }
  })

  it('surfaces the rejection reason in the error toast when sign-in fails', async () => {
    const user = userEvent.setup()
    vi.mocked(signInWithPassword).mockRejectedValueOnce(new Error('Invalid email or password.'))

    renderLoginForm()

    await user.type(screen.getByLabelText('Email'), 'admin@demo.docextract.ai')
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    // waitFor boundary: the mutation's pending -> error transition is an
    // async state update; the toast mounts when the rejection settles.
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    expect(screen.getByRole('alert')).toHaveTextContent('Invalid email or password.')
    // The browser auth vocabulary received the typed credentials, with
    // the email trimmed per the form's submit handler.
    expect(signInWithPassword).toHaveBeenCalledWith('admin@demo.docextract.ai', 'wrong-password')
  })
})
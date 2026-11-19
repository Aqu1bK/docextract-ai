import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Sign in',
};

/**
 * Placeholder for the Phase 9B sign-in screen (Supabase Auth). It exists
 * in 9A so the root redirect has a real destination and the (auth) route
 * group — screens outside the AppShell — is established.
 */
export default function LoginPage() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm border border-rule bg-paper p-8">
        <h1 className="text-lg font-semibold text-ink">Sign in</h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">
          The sign-in form arrives in Phase 9B, when Supabase Auth is wired.
        </p>
      </div>
    </main>
  );
}

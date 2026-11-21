import type { Metadata } from 'next';
import { Suspense } from 'react';

import { LoginForm } from '@/components/auth/login-form';

export const metadata: Metadata = {
  title: 'Sign in',
};

/**
 * Login page — server wrapper around the client LoginForm.
 *
 * The (auth) route group keeps this screen outside the AppShell: a
 * visitor signing in has no session yet, so there is no shell to
 * render. The Suspense boundary keeps the route statically renderable
 * while the form hydrates as a client island (the form reads
 * window.location.search in an effect, so it needs no server data).
 */
export default function LoginPage() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-6">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
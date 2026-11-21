import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { Toaster } from 'sonner';

import { Providers } from '@/components/providers';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    template: '%s | DocExtract AI',
    default: 'DocExtract AI',
  },
  description: 'Document extraction and human review platform.',
};

/**
 * Root layout — the document skeleton shared by every route.
 *
 * Fonts load here (self-hosted via next/font — no runtime Google request,
 * no CLS). The Providers component is the boundary for client-only state
 * (TanStack Query's QueryClient, created lazily per browser session).
 * The Toaster is mounted once at the root so any screen can surface toasts
 * without its own <Toaster /> instance.
 *
 * Route-group layouts below this (`(app)/layout.tsx`, `(auth)/layout.tsx`)
 * compose inside this one: `(app)` adds the AppShell with the auth guard,
 * `(auth)` stays shell-free so the login screen renders without chrome.
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-dvh bg-paper font-sans text-ink antialiased">
        <Providers>
          {children}
        </Providers>
        <Toaster
          position="bottom-right"
          toastOptions={{
            className: 'border border-rule bg-paper text-ink',
          }}
        />
      </body>
    </html>
  );
}
'use client';

import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

/**
 * Client-only providers for the app.
 *
 * The QueryClient is created lazily inside useState so each browser
 * session gets its own instance — a module-scope QueryClient would be
 * shared across users during SSR and leak cache between requests.
 * 60s staleTime is the default for most reads; individual queries can
 * override it (the document-detail blob URL uses infinity).
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
          },
        },
      }),
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
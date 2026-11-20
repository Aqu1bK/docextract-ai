import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  // Transforms JSX/TSX with the React automatic runtime (React 19).
  // Vitest's esbuild handles TS, but JSX wants the plugin.
  plugins: [react()],
  resolve: {
    alias: {
      // Mirror tsconfig.json's "@/*" → "./*" (paths are relative to
      // apps/web). ESM has no __dirname; the URL form is the portable
      // equivalent.
      '@': fileURLToPath(new URL('.', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    include: ['**/*.{test,spec}.{ts,tsx}'],
    // The 9C export row imports lib/env (the download link's base URL),
    // which fails fast on missing NEXT_PUBLIC_* values: load the test
    // env the same way a Next build loads .env.local.
    env: {
      NEXT_PUBLIC_API_URL: 'http://localhost:8000/api/v1',
      NEXT_PUBLIC_SUPABASE_URL: 'https://test.supabase.co',
      NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-anon-key',
      NEXT_PUBLIC_DEMO_MODE: 'false',
    },
  },
});
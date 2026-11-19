import { z } from 'zod';

/**
 * The complete browser-facing environment contract.
 *
 * Only these four NEXT_PUBLIC_* variables may ever be read in client code.
 * Next.js inlines NEXT_PUBLIC_* values at build time, so a wrong value is
 * frozen into the bundle — which is exactly why validation must run at
 * module load rather than "when used": a bad build should never boot.
 *
 * Server-only secrets (DATABASE_URL, JWT_SECRET, ...) never appear here by
 * design; this module must be safely importable from any client component.
 */

/** Treat an empty string ("KEY=" in a .env file) as unset. */
const emptyAsUndefined = (value: unknown) => (value === '' ? undefined : value);

const publicEnvSchema = z.object({
  /** FastAPI base URL, e.g. http://localhost:8000 — required, no default. */
  NEXT_PUBLIC_API_URL: z.string().url(),

  /**
   * Supabase project URL. Optional in 9A: local development runs without
   * auth until Phase 9B wires Supabase Auth. Required from 9B onward
   * (the login page will enforce it — this file stays lenient).
   */
  NEXT_PUBLIC_SUPABASE_URL: z.preprocess(
    emptyAsUndefined,
    z.string().url().optional(),
  ),

  /** Supabase anon key — public by design (RLS is the enforcement point). */
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.preprocess(
    emptyAsUndefined,
    z.string().min(1).optional(),
  ),

  /** Strictly 'true' | 'false'. Anything else is a typo and must fail. */
  NEXT_PUBLIC_DEMO_MODE: z.enum(['true', 'false']).default('false'),
});

export type PublicEnv = z.infer<typeof publicEnvSchema>;

function parsePublicEnv(): PublicEnv {
  const parsed = publicEnvSchema.safeParse({
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    NEXT_PUBLIC_DEMO_MODE: process.env.NEXT_PUBLIC_DEMO_MODE,
  });

  if (!parsed.success) {
    const fieldErrors = parsed.error.flatten().fieldErrors;
    const details = Object.entries(fieldErrors)
      .map(([key, messages]) => `  - ${key}: ${messages?.join(', ')}`)
      .join('\n');
    throw new Error(
      `Invalid environment variables for apps/web.\n${details}\n` +
        'Fix apps/web/.env.local (see the FRONTEND section of .env.example).',
    );
  }

  return parsed.data;
}

/**
 * Fail-fast: the first import of this module runs validation. The
 * DemoModeBanner imports `env`, so in practice the app cannot render a
 * single pixel with a broken environment.
 */
export const env: PublicEnv = parsePublicEnv();

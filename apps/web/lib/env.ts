import { z } from 'zod';

/**
 * Environment contract for the browser bundle.
 *
 * Next.js only forwards NEXT_PUBLIC_* variables to client code, which is
 * the security boundary here: the API URL and demo flag are public by
 * design, and the Supabase URL + anon key are the public client pair the
 * demo intentionally ships. Server-only secrets never enter this module.
 *
 * Validation runs at module load — a misconfigured deploy fails fast at
 * startup with the exact missing variable, not at some later render.
 *
 * Phase 9B tightens the two Supabase variables from "optional" to
 * "required": auth is now the app's front door (login, middleware session
 * refresh, API client tokens), so a missing Supabase config is a broken
 * product, not a degraded one. The old `|| null` fallbacks are gone with
 * them.
 */
const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z
    .string()
    .url('NEXT_PUBLIC_API_URL must be an absolute URL (e.g. http://localhost:8000/api/v1)'),
  NEXT_PUBLIC_SUPABASE_URL: z
    .string()
    .url('NEXT_PUBLIC_SUPABASE_URL must be an absolute URL (e.g. https://xxxx.supabase.co)'),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z
    .string()
    .min(1, 'NEXT_PUBLIC_SUPABASE_ANON_KEY is required (the anon key is public by design)'),
  NEXT_PUBLIC_DEMO_MODE: z
    .string()
    .regex(/^(true|false)$/, 'NEXT_PUBLIC_DEMO_MODE must be "true" or "false"')
    .default('false'),
});

/** The raw, Zod-validated NEXT_PUBLIC_* shape (the pre-9B access surface). */
type PublicEnv = z.infer<typeof envSchema>;

/**
 * Validate process.env against the schema and return the parsed values.
 *
 * Fail-fast: every offending variable is reported at once, so a bad
 * deploy is one readable error rather than a debugging session.
 */
function parsePublicEnv(): PublicEnv {
  const parsed = envSchema.safeParse({
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    NEXT_PUBLIC_DEMO_MODE: process.env.NEXT_PUBLIC_DEMO_MODE,
  });

  if (!parsed.success) {
    const details = parsed.error.issues
      .map((issue) => `  ${issue.path.join('.')}: ${issue.message}`)
      .join('\n');
    throw new Error(`Invalid environment variables:\n${details}`);
  }

  return parsed.data;
}

const parsedEnv = parsePublicEnv();

/**
 * Reconciled env access — raw Zod values + derived short-names.
 *
 * `supabaseUrl` / `supabaseAnonKey` / `apiBaseUrl` are the short names
 * consumed by lib/api.ts, lib/supabase-browser.ts, and
 * lib/supabase-server.ts; the NEXT_PUBLIC_* keys are the authoritative
 * values validated by the Zod schema.
 *
 * Supabase fields may be undefined in 9A (optional during early dev);
 * the short-names mirror that optionality rather than lying with `!`.
 */
export const env = {
  ...parsedEnv,
  apiBaseUrl: parsedEnv.NEXT_PUBLIC_API_URL,
  supabaseUrl: parsedEnv.NEXT_PUBLIC_SUPABASE_URL,
  supabaseAnonKey: parsedEnv.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  /** Parsed boolean — true when the demo banner should render. */
  demoMode: parsedEnv.NEXT_PUBLIC_DEMO_MODE === 'true',
};

export type Env = typeof env;
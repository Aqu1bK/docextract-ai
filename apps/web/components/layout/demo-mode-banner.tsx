'use client';

import { Info } from 'lucide-react';
import { env } from '@/lib/env';

/**
 * A 32px full-width strip — a design feature, not a debug flag. Honesty is
 * the product: a recruiter evaluating the demo must never mistake simulated
 * extraction for real extraction, so the notice is branded, permanent, and
 * explained. Renders only when NEXT_PUBLIC_DEMO_MODE === 'true'.
 */
export function DemoModeBanner() {
  if (env.NEXT_PUBLIC_DEMO_MODE !== 'true') {
    return null;
  }

  return (
    <div className="flex h-8 w-full shrink-0 items-center justify-center gap-2 border-b border-accent/20 bg-accent/8 px-4 text-accent">
      <p className="text-xs font-medium">
        Demo Mode — Extraction runs with simulated AI. No real data is
        processed.
      </p>

      {/*
        Zero-dependency popover: native <details>. Keyboard operable, works
        without JS. Does not close on outside click — acceptable for a static
        explanation; swap for a Radix popover in 9B if product wants it.
      */}
      <details className="relative">
        <summary
          className="flex cursor-pointer list-none items-center [&::-webkit-details-marker]:hidden"
          aria-label="What does demo mode mean?"
        >
          <Info className="size-3.5" aria-hidden />
        </summary>
        <div className="absolute right-0 top-full z-50 mt-2 w-80 border border-rule bg-paper p-4 shadow-sm">
          {/* Wording drafted to summarize docs/demo-mode-explanation.md
              (assumption A10) — swap for the document's own two sentences. */}
          <p className="text-xs leading-relaxed text-ink">
            Demo mode runs the full upload, extraction, and review flow against
            simulated responses, so the product can be evaluated without
            connecting storage or a model provider. Set NEXT_PUBLIC_DEMO_MODE to
            false to point this same interface at your real API.
          </p>
          {/* Placeholder target — update when a docs route exists. */}
          <a
            href="#"
            className="mt-3 inline-block text-xs font-medium text-accent hover:text-accent-hover"
          >
            Learn more
          </a>
        </div>
      </details>
    </div>
  );
}

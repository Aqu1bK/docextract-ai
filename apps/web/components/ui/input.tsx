import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * Input — hand-rolled on purpose.
 *
 * Stock shadcn's Input has no Radix dependency either (it is a bare
 * `<input>`), so this is a 1:1 adaptation with the Ink-on-Paper treatment:
 * hairline rule border, paper fill, zero radius, no shadow.
 */
function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        // Height matches Button (h-10) so Input + Button rows align.
        'flex h-10 w-full min-w-0 border border-rule bg-paper px-3 py-2 text-sm text-ink',
        'placeholder:text-ink/40 disabled:cursor-not-allowed disabled:opacity-50',
        // File input affordances (the UploadView fallback control): the
        // native file button is stripped to plain ink text.
        'file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-ink',
        // Keyboard focus comes from the global :focus-visible rule in
        // globals.css (Phase 9A) — no local focus utilities on purpose.
        //
        // Invalid state follows the login toast idiom: the hairline rule
        // border darkens to full ink instead of switching to a red.
        'aria-invalid:border-ink',
        className
      )}
      {...props}
    />
  )
}

export { Input }
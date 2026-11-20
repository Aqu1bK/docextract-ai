import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * Label — native `<label>`, no @radix-ui/react-label.
 *
 * Stock shadcn wraps Radix Label only for ref/`htmlFor` merging; this
 * project ships zero Radix (Phase 9A gate), and that wrapper buys nothing
 * here, so this is a plain label element.
 *
 * The treatment is the eyebrow register the design system uses for field
 * captions (small, medium, uppercase, tracked) — the same classes the
 * login form inlines, which can now consume this primitive instead.
 */
function Label({ className, ...props }: React.ComponentProps<'label'>) {
  return (
    <label
      data-slot="label"
      className={cn(
        'flex select-none items-center gap-2 text-xs font-medium uppercase tracking-wide text-ink/70',
        // Dims the label when the associated control is disabled. Works
        // when the control precedes the label as a `peer` sibling.
        'peer-disabled:cursor-not-allowed peer-disabled:opacity-50',
        className
      )}
      {...props}
    />
  )
}

export { Label }
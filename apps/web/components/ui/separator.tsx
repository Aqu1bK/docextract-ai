import * as React from 'react'

import { cn } from '@/lib/utils'

interface SeparatorProps extends React.ComponentProps<'div'> {
  /** Rule direction. Horizontal separators are full-width hairlines. */
  orientation?: 'horizontal' | 'vertical'
  /**
   * Decorative separators are hidden from the accessibility tree
   * (role="none"). Pass decorative={false} to expose role="separator".
   */
  decorative?: boolean
}

/**
 * Separator — a hairline rule.
 *
 * Stock shadcn wraps @radix-ui/react-separator for width/height
 * measurement and ARIA wiring; a static hairline needs none of that, so
 * this is a plain div honoring the same role contract.
 */
function Separator({
  className,
  orientation = 'horizontal',
  decorative = true,
  ...props
}: SeparatorProps) {
  return (
    <div
      role={decorative ? 'none' : 'separator'}
      // role="separator" only needs an explicit orientation when vertical;
      // horizontal is the implicit default per the ARIA spec.
      aria-orientation={decorative || orientation === 'horizontal' ? undefined : 'vertical'}
      data-slot="separator"
      className={cn(
        'shrink-0 bg-rule',
        orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px',
        className
      )}
      {...props}
    />
  )
}

export { Separator }
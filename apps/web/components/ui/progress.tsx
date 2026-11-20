import * as React from 'react'

import { cn } from '@/lib/utils'

interface ProgressProps extends React.ComponentProps<'div'> {
  /** Current value. `null`/`undefined` renders an indeterminate track. */
  value?: number | null
  /** Maximum value; the fill percentage is computed against this. */
  max?: number
}

/**
 * Progress — an ink fill on a rule track.
 *
 * Stock shadcn wraps @radix-ui/react-progress (ARIA wiring + an animated
 * indicator). The zero-Radix edition is a div implementing the same
 * `role="progressbar"` contract, with no transition: the fill jumps
 * between values, which is honest for chunky upload-progress events.
 */
function Progress({ className, value, max = 100, ...props }: ProgressProps) {
  // Clamp before computing width so a racing upload callback can never
  // push the indicator past the track, or below its start.
  const safeValue =
    typeof value === 'number' && Number.isFinite(value)
      ? Math.min(Math.max(value, 0), max)
      : null
  const percentage = safeValue === null ? null : (safeValue / max) * 100

  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={safeValue === null ? undefined : safeValue}
      aria-valuetext={percentage === null ? undefined : `${Math.round(percentage)}%`}
      data-slot="progress"
      className={cn('h-1 w-full overflow-hidden bg-rule', className)}
      {...props}
    >
      {/*
        Hidden entirely while indeterminate — no animated stripes, no
        shimmer. Nothing to report renders as nothing.
      */}
      {percentage === null ? null : (
        <div
          data-slot="progress-indicator"
          className="h-full bg-ink"
          style={{ width: `${percentage}%` }}
        />
      )}
    </div>
  )
}

export { Progress }
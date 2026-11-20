import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * Card — an Ink-on-Paper sheet.
 *
 * A card is a sheet of paper: hairline rule on all sides, paper fill, zero
 * radius, zero shadow. Stock shadcn's rounded-xl + shadow-sm are removed
 * by design — elevation is expressed with borders, never shadows.
 */
function Card({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card"
      className={cn('flex flex-col gap-6 border border-rule bg-paper py-6 text-ink', className)}
      {...props}
    />
  )
}

/**
 * Card header. Laid out as a grid so an optional <CardAction> lands in the
 * right column on the title's row; the @container query drops the action
 * below the title when the card narrows (Tailwind v4 container queries).
 */
function CardHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        '@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-1.5 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6',
        className
      )}
      {...props}
    />
  )
}

/** Card title — human register: Inter, semibold, tight leading. */
function CardTitle({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-title"
      className={cn('text-base font-semibold leading-none text-ink', className)}
      {...props}
    />
  )
}

/** Card description — secondary ink, relaxed leading for sentences. */
function CardDescription({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-description"
      className={cn('text-sm leading-relaxed text-ink/60', className)}
      {...props}
    />
  )
}

/** Card action — right column of the header grid; un-stacks when narrow. */
function CardAction({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-action"
      className={cn('col-start-2 row-span-2 row-start-1 self-start justify-self-end', className)}
      {...props}
    />
  )
}

function CardContent({ className, ...props }: React.ComponentProps<'div'>) {
  return <div data-slot="card-content" className={cn('px-6', className)} {...props} />
}

/**
 * Card footer. Add a `border-t` class to separate it with a hairline —
 * the `[.border-t]:pt-6` variant then restores matching top padding.
 */
function CardFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-footer"
      className={cn('flex items-center px-6 [.border-t]:pt-6', className)}
      {...props}
    />
  )
}

export { Card, CardHeader, CardFooter, CardTitle, CardAction, CardDescription, CardContent }
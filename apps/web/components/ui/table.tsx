import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * Table — the hairline register.
 *
 * Ink-on-Paper tables are ruled by hairlines only: every row closes with a
 * rule border, the header sits on a rule, and hover lightens the paper
 * with a whisper of ink. No zebra striping, no shadows, no transitions.
 * Headers are set in the mono eyebrow register (machine/structural
 * labels); cells stay in Inter (human data).
 */
function Table({ className, ...props }: React.ComponentProps<'table'>) {
  return (
    <div data-slot="table-container" className="relative w-full overflow-x-auto">
      <table
        data-slot="table"
        className={cn('w-full caption-bottom text-sm', className)}
        {...props}
      />
    </div>
  )
}

function TableHeader({ className, ...props }: React.ComponentProps<'thead'>) {
  return (
    <thead
      data-slot="table-header"
      className={cn('[&_tr]:border-b [&_tr]:border-rule', className)}
      {...props}
    />
  )
}

function TableBody({ className, ...props }: React.ComponentProps<'tbody'>) {
  return (
    <tbody
      data-slot="table-body"
      className={cn('[&_tr]:last:border-b-0', className)}
      {...props}
    />
  )
}

function TableFooter({ className, ...props }: React.ComponentProps<'tfoot'>) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn(
        'border-t border-rule bg-ink/[0.03] font-medium [&>tr]:last:border-b-0',
        className
      )}
      {...props}
    />
  )
}

/**
 * Row. `data-state="selected"` is honored (the shadcn contract) with a
 * slightly stronger ink wash than hover.
 */
function TableRow({ className, ...props }: React.ComponentProps<'tr'>) {
  return (
    <tr
      data-slot="table-row"
      className={cn(
        'border-b border-rule hover:bg-ink/[0.04] data-[state=selected]:bg-ink/[0.06]',
        className
      )}
      {...props}
    />
  )
}

function TableHead({ className, ...props }: React.ComponentProps<'th'>) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        'h-10 whitespace-nowrap px-3 text-left align-middle font-mono text-[11px] font-normal uppercase tracking-[0.14em] text-ink/50',
        className
      )}
      {...props}
    />
  )
}

function TableCell({ className, ...props }: React.ComponentProps<'td'>) {
  return (
    <td data-slot="table-cell" className={cn('px-3 py-3 align-middle', className)} {...props} />
  )
}

function TableCaption({ className, ...props }: React.ComponentProps<'caption'>) {
  return (
    <caption
      data-slot="table-caption"
      className={cn('caption-bottom pt-4 text-sm text-ink/50', className)}
      {...props}
    />
  )
}

export { Table, TableHeader, TableBody, TableFooter, TableHead, TableRow, TableCell, TableCaption }
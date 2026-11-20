'use client'

import { cva, type VariantProps } from 'class-variance-authority'
import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * DropdownMenu — native `<details>`/`<summary>` popover.
 *
 * This file formalizes the native-details popover pattern prototyped in the
 * Phase 9A topbar. Stock shadcn wraps @radix-ui/react-dropdown-menu for
 * portaling, focus trapping, and arrow-key roving; this project ships zero
 * Radix (Phase 9A gate), so the menu leans on the platform instead:
 *
 * - Open/close — native details behavior, mirrored into React state via
 *   onToggle so items and the dismiss effect can act on it.
 * - Keyboard  — Enter/Space/Tab on the summary trigger (native); items are
 *   real buttons, so they are tabbable and activatable by default. Arrow-
 *   key roving is a deliberate omission — we do not claim ARIA `menu`
 *   semantics we do not fully honor, so items keep `button` semantics.
 * - Dismissal — outside click and Escape close the menu (effect below).
 * - Position  — the panel is absolutely positioned inside the details
 *   root. There is no portal: keep overflow-hidden or transform-wrapping
 *   ancestors in mind when composing.
 *
 * The trigger ships without a chevron on purpose — compose your own
 * affordance (inline SVG, mono label) as trigger children.
 */
interface DropdownMenuContextValue {
  close: () => void
}

const DropdownMenuContext = React.createContext<DropdownMenuContextValue | null>(null)

function DropdownMenu({ className, children, ...props }: React.ComponentProps<'details'>) {
  const rootRef = React.useRef<HTMLDetailsElement>(null)
  const [open, setOpen] = React.useState(false)

  // Native summary clicks flip the DOM `open` attribute; onToggle mirrors
  // that change into state so items (and the dismiss effect) can react.
  function handleToggle(event: React.ToggleEvent<HTMLDetailsElement>) {
    setOpen(event.currentTarget.open)
  }

  React.useEffect(() => {
    if (!open) {
      return
    }

    function handleDocumentClick(event: MouseEvent) {
      // The summary toggles itself natively; any click that lands outside
      // the root entirely should force the menu closed.
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }

    document.addEventListener('click', handleDocumentClick)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('click', handleDocumentClick)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  return (
    <details
      {...props}
      ref={rootRef}
      open={open}
      onToggle={handleToggle}
      className={cn('relative inline-block text-left', className)}
    >
      <DropdownMenuContext.Provider value={{ close: () => setOpen(false) }}>
        {children}
      </DropdownMenuContext.Provider>
    </details>
  )
}

/**
 * Trigger — the `<summary>` element. The native disclosure triangle is
 * suppressed (Firefox via list-none, Safari/Chrome via the webkit pseudo)
 * and keyboard focus comes from the global :focus-visible rule.
 */
function DropdownMenuTrigger({ className, children, ...props }: React.ComponentProps<'summary'>) {
  return (
    <summary
      data-slot="dropdown-menu-trigger"
      className={cn(
        'flex cursor-pointer select-none list-none items-center gap-2 [&::-webkit-details-marker]:hidden',
        className
      )}
      {...props}
    >
      {children}
    </summary>
  )
}

interface DropdownMenuContentProps extends React.ComponentProps<'div'> {
  /** Horizontal anchor: start = left edges align, end = right edges align. */
  align?: 'start' | 'end'
}

function DropdownMenuContent({ className, align = 'start', ...props }: DropdownMenuContentProps) {
  return (
    <div
      data-slot="dropdown-menu-content"
      className={cn(
        'absolute top-full z-50 mt-1 min-w-44 border border-rule bg-paper py-1',
        align === 'end' ? 'right-0' : 'left-0',
        className
      )}
      {...props}
    />
  )
}

/** Group label — the mono eyebrow register, matching table headers. */
function DropdownMenuLabel({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="dropdown-menu-label"
      className={cn(
        'px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-ink/50',
        className
      )}
      {...props}
    />
  )
}

const dropdownMenuItemVariants = cva(
  'flex w-full cursor-pointer select-none items-center gap-2 px-3 py-1.5 text-left text-sm outline-none',
  {
    variants: {
      variant: {
        default: 'text-ink/80 hover:bg-ink/5 hover:text-ink',
        // Destructive emphasis is typographic, not chromatic, per Ink on
        // Paper: full ink plus semibold weight instead of a red. Swap in a
        // status token here if chromatic feedback is ever preferred.
        destructive: 'font-semibold text-ink hover:bg-ink/5',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

interface DropdownMenuItemProps
  extends React.ComponentProps<'button'>,
    VariantProps<typeof dropdownMenuItemVariants> {}

/**
 * Item — a real `<button>`. Selecting an item closes the menu (matching
 * the Radix behavior callers expect); call `event.preventDefault()` in
 * onClick to keep the menu open. For link items, render a Next <Link> and
 * compose `dropdownMenuItemVariants()` directly — the same escape hatch
 * `buttonVariants` provides for links.
 */
function DropdownMenuItem({ className, variant, onClick, ...props }: DropdownMenuItemProps) {
  const context = React.useContext(DropdownMenuContext)

  function handleClick(event: React.MouseEvent<HTMLButtonElement>) {
    onClick?.(event)
    if (!event.defaultPrevented) {
      context?.close()
    }
  }

  return (
    <button
      type="button"
      data-slot="dropdown-menu-item"
      className={cn(dropdownMenuItemVariants({ variant }), className)}
      onClick={handleClick}
      {...props}
    />
  )
}

function DropdownMenuSeparator({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="dropdown-menu-separator"
      className={cn('-mx-1 my-1 h-px bg-rule', className)}
      {...props}
    />
  )
}

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuItem,
  DropdownMenuSeparator,
  dropdownMenuItemVariants,
}
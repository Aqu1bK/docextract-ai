import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

/**
 * Code-owned primitive (not shadcn-CLI-managed — see components.json notes).
 *
 * Deviations from the upstream shadcn Button, all deliberate:
 *  - radius 0 (`rounded-none`) — the Ink-on-Paper rule
 *  - exactly two variants (default, outline) — Phase 9A scope; 9B adds more
 *    (ghost will be wanted for the user menu) as one-line cva entries
 *  - no `asChild` — upstream requires @radix-ui/react-slot, which Phase 9A
 *    forbids; reintroduce alongside 9B's shadcn CLI installs if needed
 *  - no focus utilities — the design-system focus ring in globals.css
 *    (:focus-visible, accent 2px) is the single owner of focus rendering
 *  - no decorative arrows on labels; icons, when present, ride after text
 */
const buttonVariants = cva(
  'inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-none text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*="size-"])]:size-4',
  {
    variants: {
      variant: {
        default: 'bg-accent text-white hover:bg-accent-hover',
        outline: 'border border-rule bg-transparent hover:bg-paper-muted',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 px-3 text-xs',
        lg: 'h-10 px-6',
        icon: 'size-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

type ButtonProps = React.ComponentProps<'button'> & VariantProps<typeof buttonVariants>;

/** React 19: `ref` arrives as a prop and flows through `...props`. */
function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

export { Button, buttonVariants };
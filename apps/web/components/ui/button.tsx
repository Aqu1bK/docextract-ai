import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
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
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-none font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default: 'bg-accent text-paper hover:bg-accent-hover',
        destructive: 'bg-confidence-low text-paper hover:bg-confidence-low/90',
        outline: 'border border-rule bg-paper hover:bg-paper-muted hover:text-ink',
        secondary: 'bg-paper-muted text-ink hover:bg-rule',
        ghost: 'hover:bg-paper-muted hover:text-ink',
        link: 'text-accent underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 rounded-none px-3 text-xs',
        lg: 'h-10 rounded-none px-8',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = 'Button';

export { Button, buttonVariants };
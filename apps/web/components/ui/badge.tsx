import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

/**
 * Code-owned primitive. Radius 0, hairline border, tinted fill.
 *
 * The variant set IS the domain model:
 *  - confidence-* → machine extraction scores (threshold 0.75 lives in the
 *    backend; low = red below threshold). Set in JetBrains Mono.
 *  - status-*    → human review decisions (pending/accepted/corrected/
 *                  rejected/missing). Set in Inter.
 * The typeface switch between the two groups is the provenance contract
 * from globals.css, applied to data labels.
 */
const badgeVariants = cva(
  'inline-flex items-center gap-1 whitespace-nowrap rounded-none border px-2 py-0.5 text-xs font-medium',
  {
    variants: {
      variant: {
        default: 'border-rule bg-paper-muted text-ink-muted',
        outline: 'border-rule bg-transparent text-ink/70',
        'confidence-high': 'border-confidence-high/30 bg-confidence-high/10 font-mono text-confidence-high',
        'confidence-mid': 'border-confidence-mid/30 bg-confidence-mid/10 font-mono text-confidence-mid',
        'confidence-low': 'border-confidence-low/30 bg-confidence-low/10 font-mono text-confidence-low',
        'status-pending': 'border-status-pending/30 bg-status-pending/10 text-status-pending',
        'status-accepted': 'border-status-accepted/30 bg-status-accepted/10 text-status-accepted',
        'status-corrected': 'border-status-corrected/30 bg-status-corrected/10 text-status-corrected',
        'status-rejected': 'border-status-rejected/30 bg-status-rejected/10 text-status-rejected',
        'status-missing': 'border-status-missing/30 bg-status-missing/10 text-status-missing',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

type BadgeProps = React.ComponentProps<'span'> & VariantProps<typeof badgeVariants>;

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
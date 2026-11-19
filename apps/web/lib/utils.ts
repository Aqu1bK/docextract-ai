import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Conditional + conflict-aware class name composition.
 * `cn('px-4', isActive && 'px-6')` → 'px-6' (later class wins — the
 * tailwind-merge guarantee that makes variant overrides deterministic).
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

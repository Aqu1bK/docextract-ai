'use client';

import { ChevronLeft, ChevronRight, Minus, Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';

/**
 * PdfToolbar — the viewer's controls: page navigation and zoom.
 *
 * Pure presentational component: it renders the state its parent owns
 * (current page, page count, zoom scale) and reports intent upward via
 * callbacks. Keeping it stateless means the toolbar never disagrees
 * with the viewer about what page is showing.
 */
export interface PdfToolbarProps {
  /** 1-based page number currently rendered. */
  pageNumber: number;
  /** Total pages in the loaded document (0 while loading). */
  numPages: number;
  /** Render scale multiplier: 1 = the width the viewer chose. */
  scale: number;
  /** Instruct parent to show a different page (clamped by parent). */
  onPreviousPage: () => void;
  /** Instruct parent to show a different page (clamped by parent). */
  onNextPage: () => void;
  /** Instruct parent to increase zoom (clamped by parent). */
  onZoomIn: () => void;
  /** Instruct parent to decrease zoom (clamped by parent). */
  onZoomOut: () => void;
}

/** Zoom range and step: 0.5× to 3× in 0.2 steps, flat-system defaults. */
const MIN_SCALE = 0.5;
const MAX_SCALE = 3;
const SCALE_STEP = 0.2;

export function PdfToolbar({
  pageNumber,
  numPages,
  scale,
  onPreviousPage,
  onNextPage,
  onZoomIn,
  onZoomOut,
}: PdfToolbarProps) {
  return (
    <div className="flex items-center justify-between border border-rule bg-paper px-3 py-2">
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onPreviousPage}
          disabled={pageNumber <= 1}
          aria-label="Previous page"
        >
          <ChevronLeft className="size-4" aria-hidden />
        </Button>
        <p className="min-w-20 text-center font-mono text-xs text-ink-muted">
          {numPages > 0 ? `page ${pageNumber} / ${numPages}` : 'loading…'}
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={onNextPage}
          disabled={pageNumber >= numPages}
          aria-label="Next page"
        >
          <ChevronRight className="size-4" aria-hidden />
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onZoomOut}
          disabled={scale <= MIN_SCALE}
          aria-label="Zoom out"
        >
          <Minus className="size-4" aria-hidden />
        </Button>
        <p className="min-w-12 text-center font-mono text-xs text-ink-muted">
          {Math.round(scale * 100)}%
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={onZoomIn}
          disabled={scale >= MAX_SCALE}
          aria-label="Zoom in"
        >
          <Plus className="size-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}

export { MIN_SCALE, MAX_SCALE, SCALE_STEP };
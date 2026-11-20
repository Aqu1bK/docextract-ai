'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';

import { PdfToolbar, MIN_SCALE, MAX_SCALE, SCALE_STEP } from '@/components/pdf/pdf-toolbar';
import '@/lib/pdf-worker';

/**
 * PdfViewer — renders one PDF page on a canvas with page/zoom controls.
 *
 * react-pdf's Document and Page are imported with next/dynamic +
 * { ssr: false } because pdf.js touches browser APIs (Worker, canvas)
 * the server render cannot provide; the official react-pdf Next.js
 * guidance is exactly this pattern. The worker is configured by the
 * pdf-worker module import above (react-pdf deliberately leaves
 * GlobalWorkerOptions.workerSrc as a bare name the caller must point
 * at a real, same-origin URL).
 *
 * The page renders at a base width (the column width the two-column
 * review layout gives the PDF side); zoom multiplies that width through
 * react-pdf's `scale` prop, which renders the page at
 * base-width × scale on its canvas.
 */
const Document = dynamic(() => import('react-pdf').then((mod) => mod.Document), {
  ssr: false,
  loading: () => <div className="h-96 border border-rule bg-paper-muted" aria-busy="true" />,
});
const Page = dynamic(() => import('react-pdf').then((mod) => mod.Page), {
  ssr: false,
  loading: () => <div className="h-96 border border-rule bg-paper-muted" aria-busy="true" />,
});

/** The width (px) a 100%-zoom page renders at: the review column's PDF pane. */
const BASE_PAGE_WIDTH = 640;

export interface PdfViewerProps {
  /** URL of the PDF to render (same-origin or CORS-enabled). */
  url: string;
}

export function PdfViewer({ url }: PdfViewerProps) {
  const [numPages, setNumPages] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1);
  const [loadError, setLoadError] = useState(false);

  const effectiveWidth = BASE_PAGE_WIDTH * scale;
  const lastPage = Math.max(numPages, 1);

  return (
    <div className="flex flex-col gap-3">
      <PdfToolbar
        pageNumber={pageNumber}
        numPages={numPages}
        scale={scale}
        onPreviousPage={() => setPageNumber((p) => Math.max(1, p - 1))}
        onNextPage={() => setPageNumber((p) => Math.min(lastPage, p + 1))}
        onZoomIn={() => setScale((s) => Math.min(MAX_SCALE, s + SCALE_STEP))}
        onZoomOut={() => setScale((s) => Math.max(MIN_SCALE, s - SCALE_STEP))}
      />

      {loadError ? (
        <div className="border border-rule bg-paper p-8 text-center">
          <p className="text-sm text-ink">The PDF could not be displayed.</p>
          <p className="mt-1 text-xs text-ink-muted">
            The file may still be processing, or the storage URL expired — reload the page to
            re-fetch it.
          </p>
        </div>
      ) : (
        <div
          className="overflow-auto border border-rule bg-paper-muted p-4"
          aria-label="PDF preview"
        >
          <Document
            file={url}
            onLoadSuccess={({ numPages: loaded }) => {
              setNumPages(loaded);
              setPageNumber(1);
              setLoadError(false);
            }}
            onError={() => setLoadError(true)}
          >
            <Page
              pageNumber={Math.min(pageNumber, lastPage)}
              width={effectiveWidth}
              renderTextLayer={false}
              renderAnnotationLayer={false}
            />
          </Document>
        </div>
      )}

      {numPages > 1 ? (
        <p className="text-xs text-ink-muted">
          {numPages} pages — the review fields link each value to its page in the machine column.
        </p>
      ) : null}
    </div>
  );
}

export { BASE_PAGE_WIDTH };
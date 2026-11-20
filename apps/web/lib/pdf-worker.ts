// docextract-ai/apps/web/lib/pdf-worker.ts

'use client';

import * as pdfjs from 'pdfjs-dist';
// Turbopack treats a `new URL(..., import.meta.url)` asset reference as
// the module's own public URL — the documented pattern for worker
// assets that must resolve at runtime to a real, same-origin file.
// pdf.js requires workerSrc to be same-origin with the page; the bare
// 'pdf.worker.mjs' string react-pdf ships would resolve against the
// page URL and 404.
const pdfjsWorkerUrl = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).href;

/**
 * pdf.js worker setup — the one global react-pdf needs before first use.
 *
 * react-pdf 11 deliberately does not set the worker itself: its bundle
 * assigns the bare string 'pdf.worker.mjs', which pdf.js resolves
 * against the document URL and fails to load. Assigning the bundler
 * URL for the actual worker file satisfies pdf.js's same-origin
 * requirement and runs the heavy parsing off the main thread.
 *
 * Guarded so importing this module in jsdom (tests) sets nothing: the
 * worker is a browser-only resource, and jsdom has no Web Worker.
 */
if (typeof window !== 'undefined' && 'Worker' in globalThis) {
  pdfjs.GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl;
}

export const pdfWorkerSrc = pdfjs.GlobalWorkerOptions.workerSrc;
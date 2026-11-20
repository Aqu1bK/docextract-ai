import type { Metadata } from 'next'

import { UploadView } from '@/components/upload/upload-view'
import { requireUser } from '@/lib/auth'

export const metadata: Metadata = {
  title: 'Upload',
  description: 'Upload a PDF document and queue it for the extraction pipeline.',
}

/**
 * Upload — server wrapper for the intake view.
 *
 * Same page contract as the documents route: this server component guards
 * the route and renders the chrome; `UploadView` is the client boundary that
 * owns the dropzone and the `useUploadDocument()` mutation.
 *
 * The copy below states the pipeline contract explicitly (PDF-only intake,
 * MinIO object storage, 0.75 confidence threshold) so operators can see
 * what happens to a file without reading the backend docs.
 */
export default async function UploadPage() {
  await requireUser()

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-8 sm:px-6 lg:px-10">
      <header className="flex flex-col gap-1 border-b border-rule pb-6">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/50">Intake</p>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Upload document</h1>
        <p className="max-w-prose text-sm leading-relaxed text-ink/60">
          Add a PDF to the workspace. Extraction starts as soon as the upload completes.
        </p>
      </header>

      <UploadView />

      <section aria-labelledby="upload-pipeline-notes" className="border-t border-rule pt-6">
        <h2
          id="upload-pipeline-notes"
          className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/50"
        >
          Pipeline notes
        </h2>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-ink/70">
          <li>Only PDF documents are accepted; the pipeline parses text directly from the file.</li>
          <li>Files are stored in MinIO object storage scoped to this workspace.</li>
          <li>
            Extracted fields scoring below the 0.75 confidence threshold are flagged for human
            review before they can be accepted.
          </li>
        </ol>
      </section>
    </div>
  )
}
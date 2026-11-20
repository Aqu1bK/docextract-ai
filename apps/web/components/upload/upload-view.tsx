'use client'

import Link from 'next/link'
import { useState } from 'react'

import { formatBytes, formatTimestamp } from '@/components/documents/document-row'
import { Dropzone } from '@/components/upload/dropzone'
import { Button, buttonVariants } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { ApiError } from '@/lib/api'
import { useUploadDocument } from '@/lib/queries'

/**
 * UploadView — the live half of the upload page.
 *
 * Division of ownership: the Dropzone owns the intake gate (type + size
 * feedback), this view owns staging state and the upload mutation. On
 * success the mutation's cache invalidation (configured in
 * `lib/queries.ts`) refreshes the documents list, so the register on
 * /documents is already current when the user navigates there.
 *
 * fetch-based uploads give no byte-level progress events, so the pending
 * state is textual ("Uploading…") — no invented percentage bar.
 */

/** Server errors carry a detail message; everything else is generic. */
function describeUploadFailure(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  return 'The upload failed before it reached the API. Check your connection and try again.'
}

/**
 * A provenance definition list: mono micro-labels on the left, machine
 * values on the right, hairline rules between rows. Shared by the staged
 * and success cards.
 */
function FileFacts({ facts }: { facts: Array<{ label: string; value: string; title?: string }> }) {
  return (
    <dl className="flex flex-col">
      {facts.map((fact) => (
        <div
          key={fact.label}
          className="flex items-baseline justify-between gap-6 border-b border-rule py-2.5 last:border-b-0"
        >
          <dt className="shrink-0 font-mono text-[10px] uppercase tracking-[0.18em] text-ink/50">
            {fact.label}
          </dt>
          <dd className="min-w-0 truncate font-mono text-sm text-ink" title={fact.title ?? fact.value}>
            {fact.value}
          </dd>
        </div>
      ))}
    </dl>
  )
}

export function UploadView() {
  const [stagedFile, setStagedFile] = useState<File | null>(null)
  const uploadMutation = useUploadDocument()

  function handleFileAccepted(file: File) {
    setStagedFile(file)
    // Any previous attempt's error/success state is stale the moment a
    // new file is staged.
    uploadMutation.reset()
  }

  /** Discard the staged file and any mutation state, back to the dropzone. */
  function handleReset() {
    setStagedFile(null)
    uploadMutation.reset()
  }

  function handleUpload() {
    if (!stagedFile || uploadMutation.isPending) {
      return
    }
    uploadMutation.mutate({ file: stagedFile })
  }

  const uploaded = uploadMutation.isSuccess ? uploadMutation.data : null

  return (
    <div className="flex flex-col gap-6">
      {uploaded ? (
        <Card>
          <CardHeader>
            <CardTitle>Upload complete</CardTitle>
            <CardDescription>
              The file is stored and the extraction pipeline will pick it up shortly.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FileFacts
              facts={[
                { label: 'file', value: uploaded.filename, title: uploaded.filename },
                { label: 'size', value: formatBytes(uploaded.size_bytes) },
                { label: 'uploaded', value: formatTimestamp(uploaded.created_at) },
              ]}
            />
          </CardContent>
          {/*
            CardFooter's `[.border-t]:pt-6` contract from the primitive:
            adding `border-t` here draws the separating hairline and the
            primitive restores matching top padding.
          */}
          <CardFooter className="gap-3 border-t">
            <Link href="/documents" className={buttonVariants()}>
              View documents
            </Link>
            <Button variant="outline" onClick={handleReset}>
              Upload another
            </Button>
          </CardFooter>
        </Card>
      ) : stagedFile ? (
        <Card>
          <CardHeader>
            <CardTitle>Ready to upload</CardTitle>
            <CardDescription>
              One PDF staged. Type and size were checked locally; the API enforces both again.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <FileFacts
              facts={[
                { label: 'file', value: stagedFile.name, title: stagedFile.name },
                { label: 'size', value: formatBytes(stagedFile.size) },
                { label: 'type', value: stagedFile.type || 'application/pdf' },
              ]}
            />

            {uploadMutation.isError && uploadMutation.error ? (
              <div role="alert" className="flex flex-col gap-1 border border-ink px-3 py-2.5">
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink/50">
                  error
                </span>
                <p className="text-sm leading-relaxed text-ink">
                  {describeUploadFailure(uploadMutation.error)}
                </p>
              </div>
            ) : null}
          </CardContent>
          <CardFooter className="gap-3 border-t">
            <Button onClick={handleUpload} disabled={uploadMutation.isPending} aria-busy={uploadMutation.isPending}>
              {uploadMutation.isPending ? 'Uploading…' : 'Upload document'}
            </Button>
            <Button variant="outline" onClick={handleReset} disabled={uploadMutation.isPending}>
              Choose a different file
            </Button>
          </CardFooter>
        </Card>
      ) : (
        <Dropzone onFileAccepted={handleFileAccepted} />
      )}
    </div>
  )
}
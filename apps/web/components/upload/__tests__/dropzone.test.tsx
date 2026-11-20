import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { Dropzone } from '@/components/upload/dropzone'

/**
 * Dropzone — the intake gate.
 *
 * Zero vi.mock calls in this file, by design: the behavior under test is
 * react-dropzone's own validation, so it runs real; the component owns no
 * env, router, or query dependencies. The only seams (onFileAccepted,
 * disabled) are props.
 */

/** Mirrors the component's gate: one PDF, at most 10 MB. */
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

/**
 * react-dropzone renders its file input visually hidden and without an
 * accessible name, so role/label queries cannot reach it. The type
 * selector is stable across its releases; the assertion makes the lookup
 * loud if that ever changes.
 */
function getFileInput(container: HTMLElement): HTMLInputElement {
  const input = container.querySelector<HTMLInputElement>('input[type="file"]')
  expect(input).not.toBeNull()
  return input as HTMLInputElement
}

describe('Dropzone', () => {
  it('accepts a PDF within the size gate and hands it to the parent', async () => {
    const onFileAccepted = vi.fn()
    const { container } = render(<Dropzone onFileAccepted={onFileAccepted} />)

    expect(screen.getByText('Drag a PDF here, or click to browse')).toBeInTheDocument()
    expect(screen.getByText('pdf only · max 10 MB')).toBeInTheDocument()

    const pdf = new File(['%PDF-1.7 minimal fixture'], 'invoice-2026-001.pdf', {
      type: 'application/pdf',
    })

    await userEvent.upload(getFileInput(container), pdf, {
      // WORKAROUND — user-event filters uploads against the input's
      // `accept` attribute, and react-dropzone serializes its accept
      // option to "application/pdf,.pdf", which user-event's matcher
      // routinely drops even for correctly typed files (silently — no
      // onDrop, no error). The gate under test here is react-dropzone's
      // OWN validation, so we disable user-event's redundant filtering
      // and let the component reject what it rejects.
      applyAccept: false,
    })

    // waitFor boundary: react-dropzone runs its file validation through
    // a promise chain, so the accepted callback lands a tick after the
    // change event — not synchronously inside the upload call.
    await waitFor(() => {
      expect(onFileAccepted).toHaveBeenCalledTimes(1)
    })

    // The parent receives the exact File instance, not a copy.
    expect(onFileAccepted).toHaveBeenCalledWith(pdf)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('rejects a non-PDF with the type message and never calls the parent', async () => {
    const onFileAccepted = vi.fn()
    const { container } = render(<Dropzone onFileAccepted={onFileAccepted} />)

    const textFile = new File(['plain text, not a pdf'], 'notes.txt', { type: 'text/plain' })

    await userEvent.upload(getFileInput(container), textFile, { applyAccept: false })

    // waitFor boundary: rejection messaging is derived from
    // fileRejections, which react-dropzone populates asynchronously.
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        '"notes.txt" is not a PDF — only PDF documents are accepted.'
      )
    })

    expect(onFileAccepted).not.toHaveBeenCalled()
  })

  it('rejects a PDF over the size gate with the size message', async () => {
    const onFileAccepted = vi.fn()
    const { container } = render(<Dropzone onFileAccepted={onFileAccepted} />)

    // 10 MB + 1 byte — one byte past the gate. Allocated for real
    // rather than spoofing File#size with a getter override: cheaper to
    // read in review, and jsdom does not mind 10 MB.
    const oversized = new File(
      [new Uint8Array(MAX_FILE_SIZE_BYTES + 1)],
      'annual-report.pdf',
      { type: 'application/pdf' }
    )

    await userEvent.upload(getFileInput(container), oversized, { applyAccept: false })

    // waitFor boundary: same async validation path as the type gate.
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        '"annual-report.pdf" is larger than 10 MB.'
      )
    })

    expect(onFileAccepted).not.toHaveBeenCalled()
  })
})
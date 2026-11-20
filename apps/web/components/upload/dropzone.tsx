'use client'

import { useCallback } from 'react'
import { useDropzone, type FileRejection } from 'react-dropzone'

import { cn } from '@/lib/utils'

/**
 * Client-side intake gate: one PDF, at most 10 MB.
 *
 * The limits enforced here are a convenience pass only — the API enforces
 * the same rules again server-side, so a crafted request cannot smuggle a
 * non-PDF or an oversized file past this component.
 *
 * react-dropzone is a behavior library (drag state, file dialog, MIME
 * matching), not a styling/primitives package, so it does not violate the
 * Phase 9A zero-Radix dependency gate.
 */

/** 10 MB. Kept in sync with the backend's MAX_UPLOAD_SIZE. */
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

/** Human label for the same limit, used in the hint and error copy. */
const MAX_FILE_SIZE_LABEL = '10 MB'

/** PDF only — the extraction pipeline parses text straight from the file. */
const ACCEPTED_FILES = { 'application/pdf': ['.pdf'] }

interface DropzoneProps {
  /** Called with the single file that passed the gate. */
  onFileAccepted: (file: File) => void
  /** Blocks interaction (e.g., while an upload is in flight). */
  disabled?: boolean
}

/**
 * Translate react-dropzone's rejection codes into Ink-on-Paper copy.
 * Runs against the first rejection only — `multiple: false` means a
 * rejected batch is always a single story worth telling.
 */
function describeRejection(rejection: FileRejection): string {
  const name = rejection.file.name
  const code = rejection.errors[0]?.code

  switch (code) {
    case 'file-invalid-type':
      return `"${name}" is not a PDF — only PDF documents are accepted.`
    case 'file-too-large':
      return `"${name}" is larger than ${MAX_FILE_SIZE_LABEL}.`
    case 'too-many-files':
      return 'One document at a time — drop a single PDF.'
    default:
      return `"${name}" was rejected.`
  }
}

/**
 * Dropzone — the styled drop area. Presentational by contract: it owns
 * accept/reject feedback only; the accepted file is handed to the parent
 * (UploadView), which owns staging state and the upload mutation.
 */
export function Dropzone({ onFileAccepted, disabled = false }: DropzoneProps) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length > 0) {
        onFileAccepted(accepted[0])
      }
    },
    [onFileAccepted]
  )

  const { getRootProps, getInputProps, isDragActive, isDragReject, fileRejections } =
    useDropzone({
      onDrop,
      accept: ACCEPTED_FILES,
      maxSize: MAX_FILE_SIZE_BYTES,
      multiple: false,
      disabled,
    })

  const rejectionMessage = fileRejections.length > 0 ? describeRejection(fileRejections[0]) : null

  return (
    <div className="flex flex-col gap-2">
      {/*
        Keyboard focus comes from the global :focus-visible rule in
        globals.css (react-dropzone gives the root a tabIndex). The dashed
        border is the one dashed line in the system — it marks "drop here".
      */}
      <div
        {...getRootProps()}
        className={cn(
          'flex cursor-pointer select-none flex-col items-center justify-center gap-3 border border-dashed border-rule bg-paper px-6 py-14 text-center',
          'hover:border-ink/60',
          isDragActive && !isDragReject && 'border-ink bg-ink/[0.03]',
          isDragReject && 'border-ink',
          disabled && 'pointer-events-none opacity-50'
        )}
      >
        <input {...getInputProps()} />

        {/* Hairline upload glyph — arrow down into a tray. */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className="h-8 w-8 text-ink/40"
        >
          <path d="M12 3v10m0 0l-4-4m4 4l4-4" />
          <path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
        </svg>

        <p className="text-sm text-ink">
          {isDragActive ? 'Drop the PDF to stage it' : 'Drag a PDF here, or click to browse'}
        </p>

        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink/50">
          pdf only · max {MAX_FILE_SIZE_LABEL}
        </p>
      </div>

      {/*
        Rejection feedback lives below the drop area so the drop target
        itself never shifts size while a drag is in progress.
      */}
      {rejectionMessage ? (
        <p role="alert" className="px-1 font-mono text-[11px] leading-relaxed text-ink">
          {rejectionMessage}
        </p>
      ) : null}
    </div>
  )
}
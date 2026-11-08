# ADR-003: Use pypdf Instead of PyMuPDF

## Status

Accepted

## Context

The extraction pipeline needs a Python library to pull text out of native (text-based) PDF pages — the "Light Parser" step that runs before any Vision LLM work. Two candidates were considered: pypdf and PyMuPDF.

The decisive constraint is licensing. This project is MIT-licensed, and the product contract states "no AGPL dependencies by default." PyMuPDF is licensed under AGPL-3.0, with a paid commercial license available from Artifex Software. Adding PyMuPDF as a Python dependency embeds AGPL-licensed code in the project's distribution, which conflicts with that constraint and would complicate any future commercial use of the code by a client.

Secondary constraints: the parser must be pure Python and installable anywhere the backend runs (including constrained free-tier hosting), it must handle straightforward text extraction for typical business PDFs, and heavy rendering is already covered separately by pdf2image + Poppler in Local Docker Mode.

## Decision

The Light Parser uses pypdf for text extraction from native PDF pages; PyMuPDF is not added as a dependency.

## Rationale

- **License:** pypdf is BSD-3-Clause licensed — permissive and compatible with an MIT project and with future client use. PyMuPDF's AGPL-3.0 is not, absent a commercial license purchase.
- **Sufficiency:** For native business PDFs (invoices, contracts, RFPs, bills of lading), pypdf's text extraction is adequate; the pipeline does not need MuPDF's rendering speed or low-level machinery.
- **Deployment weight:** pypdf is pure Python with no native binaries, so it installs identically on hosted and local environments. The heavier page-rendering need is met by pdf2image + Poppler as an external tool, and only in Local Docker Mode.
- **Scope honesty:** Where pypdf is not enough (scanned documents, layout-heavy extraction), the answer in this architecture is the Vision LLM in Local Docker Mode — not a heavier local parser on the hosted demo.

## Consequences

### Positive

- The repository keeps a permissive dependency tree; no AGPL obligations attach to the code.
- A pure-Python parser runs everywhere the backend runs, including free-tier hosting, with no system packages.
- The choice is consistent with the "no AGPL by default" constraint a client would check.

### Negative

- pypdf is slower than PyMuPDF on large documents and less capable on unusual PDFs (complex encodings, some CID fonts).
- Some malformed PDFs that PyMuPDF tolerates will fail extraction; such jobs end as documented `failed` states rather than being silently mishandled.
- If a future client needs PyMuPDF-grade parsing, that requires a license decision (buy commercial, or accept AGPL terms) recorded in a new ADR.

## Alternatives Considered

### Alternative 1: PyMuPDF

- Description: The Python binding for MuPDF — fast, powerful text extraction and rendering for PDFs.
- Why rejected: AGPL-3.0 license conflicts with the "no AGPL dependencies by default" constraint of this MIT-licensed project; a commercial license from Artifex costs money, contradicting the $0 budget; and its capabilities exceed what the Light Parser step requires.

### Alternative 2: No local parser — rely on the Vision LLM for everything

- Description: Skip local text extraction entirely and send every page image to the Vision LLM, even for native PDFs.
- Why rejected: Native PDFs already contain extractable text; sending it through a Vision LLM adds avoidable cost and latency, adds a failure mode where none is needed, and makes the hosted demo impossible without AI calls. The Light Parser keeps extraction of native PDFs free, fast, and deterministic.

## References

- pypdf (BSD-3-Clause, pure Python): https://pypi.org/project/pypdf
- PyMuPDF (AGPL-3.0): https://pypi.org/project/PyMuPDF
- Artifex commercial licensing for MuPDF/PyMuPDF: https://artifex.com/licensing
- pdf2image (MIT) wrapping Poppler's rendering utilities, used only in Local Docker Mode: https://github.com/Belval/pdf2image

"""Job processing: the unit of work a claimed job is run through.

One function takes a claimed LEASED job to SUCCEEDED or raises: it
flips the job and document to their processing states, builds the
provider the job's ``mode`` names (the light parser needs the document's
bytes bound at construction), awaits the provider's ``extract``, and
persists the result. Routing comes last: any field scoring below
``CONFIDENCE_THRESHOLD`` sends the document to needs_review, else
ready_for_review — the confidence dial from Phase 6 deciding the human
workload of Phase 8.

Failures propagate to the caller (the runner) unchanged: this module
decides nothing about retries, so classification stays testable and the
processing step stays single-purpose.
"""

import datetime
import decimal

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import AuditLog, Document, ExtractionJob
from app.domain.enums import DocumentStatus, JobStatus
from app.extraction.base import ExtractionProvider
from app.schemas.extraction import ExtractionResult
from app.workers.persistence import persist_extraction_results

logger = structlog.get_logger(__name__)


def _build_provider(
    job: ExtractionJob, document: Document, settings: Settings
) -> ExtractionProvider:
    """Return the extraction provider the job's mode names.

    The light parser is the only mode needing the document's bytes (its
    constructor binding, Phase 6); the mock reads nothing. Storage
    download errors here propagate as-is for classification upstream.
    """
    if job.mode == "light_parser":
        from app.extraction.light_parser_provider import LightParserProvider

        data = _download_document_bytes(document.storage_path)
        return LightParserProvider(document_bytes=data)
    # The remaining modes (mock now, vision_llm from Phase 10) are built
    # by the factory from EXTRACTION_MODE; a job's mode and the setting
    # agree because creation stamped the setting onto the row.
    from app.extraction.factory import get_extraction_provider

    return get_extraction_provider()


def _download_document_bytes(storage_path: str) -> bytes:
    """Download one document's bytes from the configured storage backend.

    The storage factory reads the same env the worker process was
    started with; download is the provider-agnostic step the light
    parser's constructor binding needs.
    """
    from app.storage.factory import get_storage

    return get_storage().download_file(storage_path)


async def process_job(session: Session, job: ExtractionJob, settings: Settings) -> None:
    """Run one claimed job to completion (SUCCEEDED) or raise its failure.

    Args:
        session: The worker's session (caller owns commit/rollback).
        job: The claimed job, expected in LEASED status.
        settings: Application settings (threshold, storage wiring).

    Raises:
        Exception: Whatever the provider or storage raised — the runner
            classifies and schedules retries; nothing is swallowed here.
    """
    job.status = JobStatus.RUNNING
    session.flush()

    document = session.execute(select(Document).where(Document.id == job.document_id)).scalar_one()
    document.status = DocumentStatus.PROCESSING
    session.flush()

    provider = _build_provider(job, document, settings)
    result: ExtractionResult = await provider.extract(str(document.id), document.storage_path)

    persist_extraction_results(session, job, document, result, settings)

    job.status = JobStatus.SUCCEEDED
    job.completed_at = datetime.datetime.now(tz=datetime.UTC)
    job.result_metadata = dict(result.metadata)
    session.flush()

    if result.fields and any(
        field.confidence < settings.CONFIDENCE_THRESHOLD for field in result.fields
    ):
        document.status = DocumentStatus.NEEDS_REVIEW
    else:
        document.status = DocumentStatus.READY_FOR_REVIEW
    if result.document_type_prediction is not None:
        document.document_type = result.document_type_prediction.type
        document.document_type_confidence = decimal.Decimal(
            str(result.document_type_prediction.confidence)
        )
    session.flush()

    session.add(
        AuditLog(
            organization_id=job.organization_id,
            actor_user_id=None,
            action="completed",
            entity_type="extraction_job",
            entity_id=str(job.id),
            metadata_json={
                "field_count": len(result.fields),
                "table_count": len(result.tables),
                "processing_time_seconds": result.processing_time_seconds,
                "document_status": document.status.value,
            },
        )
    )
    session.flush()
    logger.info(
        "job_completed",
        job_id=str(job.id),
        document_id=str(document.id),
        field_count=len(result.fields),
        table_count=len(result.tables),
    )

"""Response model for audit log rows.

Audit rows are read-only over the API surface this phase exposes (the
trail is queried for the review history it records); the schema carries
the fields an auditor filters and sorts on — action, entity, actor, and
the structured metadata — with ``from_attributes`` so it serializes
directly from the ORM row.
"""

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    """The public view of one append-only audit row.

    ``actor_user_id`` is nullable because some audited actions are
    system-initiated (a worker finishing a job); the actor is whoever
    held the pen, human or process.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: str
    metadata_json: dict[str, Any]
    created_at: datetime.datetime

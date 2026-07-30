"""Write audit_log entries in the same transaction as the change (Decision #21)."""

import uuid as uuid_lib

from sqlalchemy.orm import Session

from app.models.meta import AuditLog


def record_audit(
    db: Session,
    *,
    entity_type: str,
    entity_uuid: uuid_lib.UUID,
    operation: str,
    entity_mnemonic: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    changed_by: uuid_lib.UUID | None = None,
    correlation_id: uuid_lib.UUID | None = None,
    source_channel: str = "api",
) -> AuditLog:
    """Persist a before/after audit entry. operation: create/update/delete/restore."""
    entry = AuditLog(
        entity_type=entity_type,
        entity_uuid=entity_uuid,
        entity_mnemonic=entity_mnemonic,
        operation=operation,
        before=before,
        after=after,
        changed_by=changed_by,
        correlation_id=correlation_id,
        source_channel=source_channel,
    )
    db.add(entry)
    return entry
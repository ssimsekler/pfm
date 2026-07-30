"""Emit CloudEvents 1.0 into the transactional outbox (Decision #5/#8/#12).

Events are written in the SAME DB transaction as the state change, so data and
events never diverge. A worker loop later relays `pending` rows to a sink/broker.
"""

import uuid as uuid_lib
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.meta import EventOutbox

SOURCE_PREFIX = "/pfm"


def emit_event(
    db: Session,
    *,
    event_type: str,
    subject: str | None = None,
    data: dict | None = None,
    source: str | None = None,
    correlation_id: uuid_lib.UUID | None = None,
) -> EventOutbox:
    """Create a CloudEvents-compliant outbox row (state-changing ops only).

    event_type example: "com.pfm.transaction.created".
    """
    event = EventOutbox(
        id=correlation_id or uuid_lib.uuid4(),
        source=source or f"{SOURCE_PREFIX}/backend",
        type=event_type,
        subject=subject,
        time=datetime.now(timezone.utc),
        datacontenttype="application/json",
        data=data or {},
        status="pending",
        attempts=0,
    )
    db.add(event)
    return event
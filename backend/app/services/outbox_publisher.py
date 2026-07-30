"""Scheduled background jobs (run by the worker via APScheduler).

Each job opens its own DB session. Jobs are defensive (never raise) so one failure
doesn't stop the scheduler.
"""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import scheduling as sch
from app.models.meta import EventOutbox
from app.models.notifications import Notification  # noqa: F401 (ensure table registered)
from app.services import notifications


def publish_pending(db: Session, batch_size: int = 100) -> int:
    """Relay pending outbox events to the sink and mark them published.

    In this dev setup there is no external broker, so we "publish" by logging
    the CloudEvent and marking the row `published`. Returns the count relayed.
    Defensive per-row handling keeps one bad event from blocking the batch.
    """
    rows = db.execute(
        select(EventOutbox)
        .where(EventOutbox.status == "pending")
        .order_by(EventOutbox.time.asc())
        .limit(batch_size)
    ).scalars().all()

    published = 0
    for event in rows:
        try:
            print(
                f"[outbox] publish id={event.id} type={event.type} subject={event.subject}",
                flush=True,
            )
            event.status = "published"
            event.attempts = (event.attempts or 0) + 1
            event.last_error = None
            published += 1
        except Exception as exc:  # noqa: BLE001
            event.status = "pending"
            event.attempts = (event.attempts or 0) + 1
            event.last_error = str(exc)
    db.commit()
    return published


def publish_outbox_job() -> None:
    db = SessionLocal()
    try:
        publish_pending(db)
    except Exception as exc:  # noqa: BLE001
        print(f"[job:outbox] error: {exc}", flush=True)
    finally:
        db.close()


def installment_due_reminders_job(horizon_days: int = 7) -> None:
    """Notify for installments due within the horizon that aren't paid."""
    db = SessionLocal()
    try:
        until = date.today() + timedelta(days=horizon_days)
        rows = db.execute(
            select(sch.InstallmentSchedule).where(
                sch.InstallmentSchedule.due_date <= until,
                sch.InstallmentSchedule.linked_txn_id.is_(None),
            )
        ).scalars()
        for row in rows:
            notifications.create_notification(
                db,
                subject=f"Installment due {row.due_date.isoformat()}",
                body=f"Installment seq {row.seq} of amount {row.amount} is due.",
                type_code="installment_due",
                related_entity_type="installment_schedule",
                related_entity_uuid=row.uuid,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"[job:installment_due] error: {exc}", flush=True)
    finally:
        db.close()


def loan_due_reminders_job(horizon_days: int = 7) -> None:
    """Notify for amortization periods due within the horizon that aren't paid."""
    db = SessionLocal()
    try:
        until = date.today() + timedelta(days=horizon_days)
        rows = db.execute(
            select(sch.AmortizationSchedule).where(
                sch.AmortizationSchedule.due_date <= until,
                sch.AmortizationSchedule.linked_txn_id.is_(None),
            )
        ).scalars()
        for row in rows:
            notifications.create_notification(
                db,
                subject=f"Loan payment due {row.due_date.isoformat()}",
                body=f"Loan period {row.period}: principal {row.principal_portion} + interest {row.interest_portion}.",
                type_code="loan_due",
                related_entity_type="amortization_schedule",
                related_entity_uuid=row.uuid,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"[job:loan_due] error: {exc}", flush=True)
    finally:
        db.close()
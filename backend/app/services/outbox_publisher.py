"""Scheduled background jobs (run by the worker via APScheduler).

Each job opens its own DB session. Jobs are defensive (never raise) so one failure
doesn't stop the scheduler.
"""

from datetime import date, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import scheduling as sch
from app.models.notifications import Notification  # noqa: F401 (ensure table registered)
from app.services import notifications, outbox_publisher


def publish_outbox_job() -> None:
    db = SessionLocal()
    try:
        outbox_publisher.publish_pending(db)
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
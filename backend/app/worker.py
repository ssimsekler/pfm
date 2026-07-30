"""PFM background worker (Phase 7).

Runs scheduled jobs via APScheduler:
  - outbox relay (publish pending CloudEvents)         — every 30s
  - installment due reminders                          — daily
  - loan payment due reminders                         — daily

Started as its own container: `python -m app.worker`. Shares the same image and
DB as the API. Jobs are defensive (they never raise), so a single failure does
not stop the scheduler.
"""

import signal

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.bootstrap import init_db
from app.services.outbox_publisher import (
    installment_due_reminders_job,
    loan_due_reminders_job,
    publish_outbox_job,
)


def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="UTC")

    # Relay outbox events frequently.
    scheduler.add_job(
        publish_outbox_job,
        IntervalTrigger(seconds=30),
        id="publish_outbox",
        max_instances=1,
        coalesce=True,
    )

    # Daily reminder sweeps (early morning UTC).
    scheduler.add_job(
        installment_due_reminders_job,
        CronTrigger(hour=6, minute=0),
        id="installment_due_reminders",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        loan_due_reminders_job,
        CronTrigger(hour=6, minute=5),
        id="loan_due_reminders",
        max_instances=1,
        coalesce=True,
    )
    return scheduler


def main() -> None:
    # Ensure schema/seed exist (idempotent; also lets the worker start
    # independently of the API container).
    init_db()

    scheduler = build_scheduler()

    def _shutdown(signum, frame):  # noqa: ANN001, ARG001
        print("[worker] shutting down…", flush=True)
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    print("[worker] scheduler starting (outbox=30s, reminders=daily).", flush=True)
    scheduler.start()


if __name__ == "__main__":
    main()
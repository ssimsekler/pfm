"""PFM background worker.

Phase 0: a minimal loop placeholder. In later phases this hosts APScheduler jobs
(FX/valuation refresh, recurring reminders, budget/installment alerts) and the
transactional outbox publisher (CloudEvents).
"""

import time


def main() -> None:
    print("[worker] PFM worker started (Phase 0 placeholder).", flush=True)
    while True:
        # Placeholder heartbeat; real jobs are wired in Phase 4/7.
        time.sleep(30)


if __name__ == "__main__":
    main()
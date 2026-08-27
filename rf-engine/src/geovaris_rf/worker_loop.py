"""GeoVaris RF development worker loop.

Continuously watches for pending RF coverage runs and dispatches them
to the appropriate model-specific worker.

Supported development models:
- ntia_itm
- free_space_test

This is an MVP development orchestration loop, not the final
production job-queue implementation.
"""

from __future__ import annotations

import time

from geovaris_rf.itm_worker import process_one_itm_run
from geovaris_rf.worker import process_one_run


POLL_INTERVAL_SECONDS = 3.0


def process_one_available_run() -> bool:
    """Process one pending RF run from a supported model.

    NTIA ITM is checked first because it is the primary validated
    terrain-aware propagation path.

    Returns True if any worker processed a run.
    Returns False if no supported pending run was available.
    """

    if process_one_itm_run():
        return True

    if process_one_run():
        return True

    return False


def run_worker_loop() -> None:
    """Continuously process supported pending RF coverage runs."""

    print("GeoVaris RF development worker started.")
    print(
        "Supported models: ntia_itm, free_space_test"
    )
    print(
        f"Polling every {POLL_INTERVAL_SECONDS:.1f} seconds."
    )
    print("Press Ctrl+C to stop.")

    try:
        while True:
            processed_run = process_one_available_run()

            if not processed_run:
                time.sleep(
                    POLL_INTERVAL_SECONDS
                )

    except KeyboardInterrupt:
        print()
        print("GeoVaris RF development worker stopped.")


if __name__ == "__main__":
    run_worker_loop()
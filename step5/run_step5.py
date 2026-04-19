"""
Step 5 Entry Point
====================
Run: python -m step5.run_step5
"""

import sys
import logging
import time

from step5.pipeline import run_step5


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            "step5/output/step5.log", mode="w", encoding="utf-8"
        ),
    ]

    logging.basicConfig(level=logging.INFO, format=log_format, handlers=handlers)
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Starting Step 5: Local Storage & Organization")
    logger.info("=" * 60)

    start = time.time()

    try:
        result = run_step5()
        elapsed = time.time() - start
        logger.info("=" * 60)
        logger.info(
            f"Step 5 complete in {elapsed:.0f}s. "
            f"{result.get('papers_organized', 0)} papers organized."
        )
    except Exception as e:
        logger.error(f"Step 5 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

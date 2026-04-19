"""
Step 4 Entry Point
====================
Run: python -m step4.run_step4
"""

import sys
import logging
import time
from datetime import datetime

from step4.pipeline import run_step4


def main():
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            "step4/output/step4.log", mode="w", encoding="utf-8"
        ),
    ]

    logging.basicConfig(level=logging.INFO, format=log_format, handlers=handlers)
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Starting Step 4: Dataset Type Classification")
    logger.info("=" * 60)

    start = time.time()

    try:
        result = run_step4()
        elapsed = time.time() - start
        logger.info("=" * 60)
        logger.info(
            f"Step 4 complete in {elapsed:.0f}s. "
            f"{result.get('both_type_count', 0)} papers with BOTH types "
            f"out of {result.get('total_processed', 0)} processed."
        )
    except Exception as e:
        logger.error(f"Step 4 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

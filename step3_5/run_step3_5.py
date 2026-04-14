"""
Step 3.5 Entry Point
====================
Run: python -m step3_5.run_step3_5
"""

import logging
import sys
import time

from step3_5.pipeline import run_step3_5


def main():
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("step3_5/output/step3_5.log", mode="w", encoding="utf-8"),
    ]
    logging.basicConfig(level=logging.INFO, format=log_format, handlers=handlers)
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Starting Step 3.5: Script-Assisted Type1 Reproduction")
    logger.info("=" * 60)

    start = time.time()
    try:
        result = run_step3_5()
        elapsed = time.time() - start
        logger.info("=" * 60)
        logger.info(
            f"Step 3.5 complete in {elapsed:.0f}s. "
            f"{result.get('both_via_script_count', 0)} papers upgraded via scripts "
            f"out of {result.get('total_candidates', 0)} candidates."
        )
    except Exception as exc:
        logger.error(f"Step 3.5 failed: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

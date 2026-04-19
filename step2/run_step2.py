"""
Step 2 Entry Point: Dataset Presence and Inventory Check
=========================================================
Usage:
    python -m step2.run_step2
"""

import sys
import logging
import time

from step2.pipeline import run_step2


def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Starting Step 2: Dataset Presence and Inventory Check")
    logger.info("=" * 60)

    start = time.time()

    try:
        result = run_step2()
        elapsed = time.time() - start

        logger.info("=" * 60)
        if result.get("status") == "success":
            logger.info(
                f"Step 2 complete in {elapsed:.0f}s. "
                f"{result['papers_with_data']} papers with dataset evidence; "
                f"{result['papers_with_data_and_pdf']} have both dataset evidence and a resolved PDF; "
                f"{result['verified_status_count']} are status=verified; "
                f"{result['papers_with_inventory']} have successful repository inventories "
                f"out of {result['candidates_processed']} processed."
            )
        elif result.get("status") == "empty":
            logger.warning("Step 2: No candidates to process.")
        else:
            logger.error(f"Step 2 finished with status: {result.get('status')}")

    except Exception as e:
        logger.error(f"Step 2 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

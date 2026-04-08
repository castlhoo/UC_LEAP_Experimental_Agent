"""
Step 5 Entry Point
====================
Run: python -m step5.run_step5
"""

import sys
import time
import logging

from step5.pipeline import run_step5

import os
os.makedirs("step5/output", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("step5/output/step5.log", mode="w", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Step 5: Dataset Summary, Task Generation & Reproducibility")
    logger.info("=" * 60)

    t0 = time.time()
    result = run_step5()
    elapsed = time.time() - t0

    logger.info("=" * 60)
    logger.info(
        f"Step 5 complete in {elapsed:.0f}s. "
        f"{result.get('total_tasks', 0)} tasks generated for "
        f"{result.get('papers_processed', 0)} papers."
    )

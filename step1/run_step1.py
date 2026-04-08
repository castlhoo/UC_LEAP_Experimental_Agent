"""
Step 1 Entry Point
===================
Run the candidate paper search pipeline.

Usage:
    python -m step1.run_step1
    or
    python step1/run_step1.py
"""

import os
import sys
import logging

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from step1.pipeline import run_step1


def setup_logging():
    """Configure logging for Step 1."""
    step1_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(step1_dir, "output")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "step1_run.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Starting Step 1: Candidate Paper Search")
    logger.info("=" * 60)

    step1_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(step1_dir, "config")
    output_dir = os.path.join(step1_dir, "output")

    try:
        candidates = run_step1(config_dir=config_dir, output_dir=output_dir)
        keep = sum(1 for c in candidates if c["screening_decision"] == "keep")
        maybe = sum(1 for c in candidates if c["screening_decision"] == "maybe")
        logger.info(f"Step 1 complete. {keep} keep + {maybe} maybe = {keep+maybe} candidates for Step 2.")
    except KeyboardInterrupt:
        logger.info("Step 1 interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Step 1 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

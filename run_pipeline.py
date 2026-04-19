"""
Unified pipeline entry point.

Run:
    python run_pipeline.py
or
    python -m run_pipeline
"""

import argparse
import logging
import os
import sys
import time
from typing import Callable, Dict, List, Tuple


project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from step1.run_step1 import main as step1_main
from step2.run_step2 import main as step2_main
from step3.run_step3 import main as step3_main
from step4.run_step4 import main as step4_main
from step5.run_step5 import main as step5_main


def setup_logging() -> None:
    os.makedirs(os.path.join(project_root, "logs"), exist_ok=True)
    log_file = os.path.join(project_root, "logs", "pipeline_run.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        ],
    )


def _run_step(name: str, fn: Callable[[], None]) -> Dict[str, float]:
    logger = logging.getLogger(__name__)
    logger.info("=" * 72)
    logger.info(f"Running {name}")
    logger.info("=" * 72)

    start = time.time()
    fn()
    elapsed = time.time() - start

    logger.info(f"{name} finished in {elapsed:.0f}s")
    return {"elapsed_seconds": elapsed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run UC_LEAP pipeline")
    parser.add_argument("--from", dest="from_step", type=str, default="1",
                        help="Start from step (1, 2, 3, 4, 5)")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)

    steps: List[Tuple[str, Callable[[], None]]] = [
        ("Step 1", step1_main),
        ("Step 2", step2_main),
        ("Step 3", step3_main),
        ("Step 4", step4_main),
        ("Step 5", step5_main),
    ]

    step_keys = ["1", "2", "3", "4", "5"]
    start_idx = 0
    if args.from_step in step_keys:
        start_idx = step_keys.index(args.from_step)
    else:
        logger.warning(f"Unknown step '{args.from_step}', starting from Step 1")

    if start_idx > 0:
        logger.info(f"Skipping steps before Step {step_keys[start_idx]}")

    summary: Dict[str, Dict[str, float]] = {}
    overall_start = time.time()

    try:
        for i, (name, fn) in enumerate(steps):
            if i < start_idx:
                logger.info(f"Skipping {name}")
                continue
            summary[name] = _run_step(name, fn)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        logger.error(f"Pipeline stopped during execution. Exit code: {code}")
        logger.info("Completed steps before failure:")
        for step_name, info in summary.items():
            logger.info(f"  - {step_name}: {info['elapsed_seconds']:.0f}s")
        sys.exit(code)
    except Exception as exc:
        logger.error(f"Pipeline failed unexpectedly: {exc}", exc_info=True)
        logger.info("Completed steps before failure:")
        for step_name, info in summary.items():
            logger.info(f"  - {step_name}: {info['elapsed_seconds']:.0f}s")
        sys.exit(1)

    total_elapsed = time.time() - overall_start
    logger.info("=" * 72)
    logger.info("Unified pipeline complete.")
    for step_name, info in summary.items():
        logger.info(f"  - {step_name}: {info['elapsed_seconds']:.0f}s")
    logger.info(f"Total elapsed: {total_elapsed:.0f}s")
    logger.info("=" * 72)


if __name__ == "__main__":
    main()

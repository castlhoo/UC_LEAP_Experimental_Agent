"""
Shared utilities for the UC_LEAP pipeline.
"""

import os
import glob
import logging

logger = logging.getLogger(__name__)


def cleanup_old_versions(output_dir: str, prefix: str, latest_suffix: str = "_latest"):
    """
    Remove old timestamped files, keeping only the 'latest' symlink/copy.

    Deletes files matching '{prefix}*' in output_dir EXCEPT those containing
    the latest_suffix (e.g., '_latest').

    Args:
        output_dir: Directory containing output files
        prefix: File prefix to match (e.g., 'step3_classification', 'manifest', 'step5_manifest')
        latest_suffix: Suffix that marks the latest file (won't be deleted)
    """
    pattern = os.path.join(output_dir, f"{prefix}*")
    for path in glob.glob(pattern):
        basename = os.path.basename(path)
        if latest_suffix in basename:
            continue
        if os.path.isfile(path):
            try:
                os.remove(path)
                logger.debug(f"  Removed old version: {basename}")
            except OSError as e:
                logger.warning(f"  Failed to remove {basename}: {e}")


def save_with_latest(data, output_dir: str, prefix: str, ext: str = ".json",
                     write_fn=None):
    """
    Save output with a timestamped filename and a '_latest' copy.
    Automatically removes previous timestamped versions.

    Args:
        data: Data to save
        output_dir: Output directory
        prefix: File prefix (e.g., 'step3_classification')
        ext: File extension
        write_fn: Callable(path, data) to write the file. If None, writes JSON.

    Returns:
        Path to the latest file
    """
    from datetime import datetime
    import json

    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_path = os.path.join(output_dir, f"{prefix}_{timestamp}{ext}")
    latest_path = os.path.join(output_dir, f"{prefix}_latest{ext}")

    if write_fn:
        write_fn(ts_path, data)
        write_fn(latest_path, data)
    else:
        for path in [ts_path, latest_path]:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    # Only remove old timestamped outputs after the new files were written.
    cleanup_old_versions(output_dir, prefix)

    return latest_path

"""Execute patched scripts inside Step 3.5 workdirs."""

import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict


def execute_target_script(script_path: str, bundle_dir: str, config: Dict[str, Any]) -> Dict[str, Any]:
    path = Path(script_path)
    ext = path.suffix.lower()
    timeout = int(config.get("execution", {}).get("timeout_sec", 180))
    before = _snapshot_files(bundle_dir)

    if ext == ".py":
        cmd = [config.get("execution", {}).get("python_command", "python"), str(path)]
    elif ext == ".ipynb":
        notebook_cmd = config.get("execution", {}).get("notebook_command", "jupyter nbconvert --to notebook --execute")
        cmd = shlex.split(notebook_cmd) + [str(path), "--output", path.name]
    else:
        return {"success": False, "status": "unsupported_language", "stdout": "", "stderr": f"Unsupported executable type: {ext}", "generated_files": []}

    try:
        proc = subprocess.run(cmd, cwd=bundle_dir, capture_output=True, text=True, timeout=timeout)
        after = _snapshot_files(bundle_dir)
        generated = sorted(after - before)
        return {
            "success": proc.returncode == 0,
            "status": "success" if proc.returncode == 0 else "failed_runtime",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "generated_files": generated,
        }
    except subprocess.TimeoutExpired as exc:
        return {"success": False, "status": "failed_timeout", "stdout": exc.stdout or "", "stderr": exc.stderr or "", "generated_files": []}
    except FileNotFoundError as exc:
        return {"success": False, "status": "failed_dependency", "stdout": "", "stderr": str(exc), "generated_files": []}


def _snapshot_files(root: str) -> set[str]:
    base = Path(root)
    files = set()
    for path in base.rglob('*'):
        if path.is_file():
            files.add(str(path.relative_to(base)).replace("\\", "/"))
    return files

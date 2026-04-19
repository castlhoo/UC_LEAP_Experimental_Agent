"""
Step 3 - File Inspector
=========================
Open and inspect downloaded dataset files to extract:
  - CSV/XLSX/TXT: column headers, sample rows, shape, data types
  - H5/HDF5: group structure, dataset shapes, dtypes
  - ZIP: file listing (if not already extracted)
  - General: file size, extension, encoding guess
"""

import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def inspect_file(file_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inspect a single file and extract content summary.

    Returns:
        Dict with file metadata and content preview.
    """
    if not os.path.isfile(file_path):
        return {"error": f"File not found: {file_path}"}

    fname = os.path.basename(file_path)
    ext = _get_extension(fname)
    stem = os.path.splitext(fname.lower())[0]
    size = os.path.getsize(file_path)

    base_info = {
        "filename": fname,
        "local_path": file_path,
        "extension": ext,
        "size_bytes": size,
        "size_human": _human_size(size),
        "file_type": "unknown",
    }

    try:
        if ext in (".csv", ".tsv", ".txt", ".dat"):
            return {**base_info, **_inspect_tabular_text(file_path, ext, config)}
        elif ext in (".xlsx", ".xls"):
            return {**base_info, **_inspect_excel(file_path, config)}
        elif ext in (".h5", ".hdf5", ".nxs"):
            return {**base_info, **_inspect_hdf5(file_path, config)}
        elif ext == ".json":
            return {**base_info, **_inspect_json(file_path, config)}
        elif ext in (".npz", ".npy"):
            return {**base_info, **_inspect_numpy(file_path, config)}
        elif ext == ".mat":
            return {**base_info, **_inspect_mat(file_path, config)}
        elif ext == ".pdf":
            return {**base_info, "file_type": "pdf", "note": "PDF file, cannot inspect data content"}
        elif ext in (".tif", ".tiff"):
            return {**base_info, "file_type": "microscopy_image",
                    "note": f"TIFF image file ({_human_size(size)}), likely raw microscopy/instrument data (STEM, SEM, AFM, etc.)"}
        elif ext in (".png", ".jpg", ".jpeg"):
            return {**base_info, "file_type": "optical_image",
                    "note": f"Image file ({ext}, {_human_size(size)}), may be optical microscopy/sample-geometry data or a rendered figure depending on paper/repository context"}
        elif ext in (".sxm", ".ibw", ".spe"):
            return {**base_info, "file_type": "instrument_raw",
                    "note": f"Raw instrument file ({ext}): scanning probe (.sxm), Igor binary (.ibw), or spectrum (.spe)"}
        elif ext in (".py", ".m", ".ipynb", ".r"):
            return {**base_info, "file_type": "script",
                    "note": f"Script or notebook file ({ext}; analysis or plotting code)"}
        elif ext in (".md", ".rst", ".yaml", ".yml") or _looks_like_documentation(stem, fname):
            return {**base_info, "file_type": "documentation",
                    "note": "README, metadata, license, or dataset description file"}
        elif ext in (".zip", ".tar", ".tar.gz", ".tgz", ".gz"):
            return {**base_info, "file_type": "archive", "note": "Archive file"}
        else:
            return {**base_info, "file_type": "binary", "note": f"Unknown format: {ext}"}
    except Exception as e:
        logger.debug(f"Inspection failed for {fname}: {e}")
        return {**base_info, "error": str(e)[:300]}


def inspect_all_files(
    download_result: Dict[str, Any],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Inspect all downloaded files for a paper."""
    reports = []
    base_dir = download_result.get("download_dir", "")

    def _relative_to_base(path: str) -> str:
        if base_dir and path:
            try:
                return os.path.relpath(path, base_dir).replace("\\", "/")
            except ValueError:
                pass
        return os.path.basename(path)

    # Inspect directly downloaded files
    for f in download_result.get("files", []):
        path = f.get("local_path", "")
        if path and os.path.isfile(path):
            report = inspect_file(path, config)
            report["download_source"] = f.get("source", "unknown")
            report["relative_path"] = _relative_to_base(path)
            reports.append(report)

    # Inspect extracted ZIP contents
    for f in download_result.get("zip_extracted", []):
        path = f.get("local_path", "")
        if path and os.path.isfile(path):
            report = inspect_file(path, config)
            report["download_source"] = "zip_extracted"
            report["archive_path"] = f.get("archive_path", "")
            report["from_zip"] = f.get("from_zip", "")
            report["relative_path"] = _relative_to_base(path)
            reports.append(report)

    return reports


# ===================================================================
# Format-specific inspectors
# ===================================================================

def _inspect_tabular_text(
    path: str, ext: str, config: Dict[str, Any]
) -> Dict[str, Any]:
    """Inspect CSV/TSV/TXT/DAT tabular data files."""
    import pandas as pd

    preview_rows = config.get("csv_preview_rows", 10)
    max_cols = config.get("max_columns_display", 30)

    result = {"file_type": "tabular_text"}

    # Try different separators
    separators = {
        ".csv": ",",
        ".tsv": "\t",
        ".txt": None,  # auto-detect
        ".dat": None,
    }
    sep = separators.get(ext)

    try:
        # Read with pandas
        if sep is None:
            # Try tab first, then whitespace, then comma
            for try_sep in ["\t", r"\s+", ","]:
                try:
                    df = pd.read_csv(
                        path, sep=try_sep, nrows=preview_rows + 5,
                        encoding="utf-8", on_bad_lines="skip",
                        engine="python" if try_sep == r"\s+" else "c",
                    )
                    if len(df.columns) > 1:
                        break
                except Exception:
                    continue
            else:
                df = pd.read_csv(
                    path, nrows=preview_rows + 5,
                    encoding="utf-8", on_bad_lines="skip",
                )
        else:
            df = pd.read_csv(
                path, sep=sep, nrows=preview_rows + 5,
                encoding="utf-8", on_bad_lines="skip",
            )

        # Count total rows (efficiently)
        total_rows = sum(1 for _ in open(path, "r", encoding="utf-8", errors="ignore")) - 1

        columns = list(df.columns[:max_cols])
        dtypes = {str(c): str(df[c].dtype) for c in columns}

        # Sample data (first few rows as strings)
        sample = df.head(preview_rows).to_dict(orient="records")
        # Truncate long values
        for row in sample:
            for k, v in row.items():
                s = str(v)
                if len(s) > 100:
                    row[k] = s[:100] + "..."

        result.update({
            "columns": columns,
            "column_count": len(df.columns),
            "row_count": total_rows,
            "dtypes": dtypes,
            "sample_rows": sample[:5],
            "has_header": _looks_like_header(columns),
            "has_numeric_data": any("float" in str(d) or "int" in str(d) for d in dtypes.values()),
        })

    except UnicodeDecodeError:
        # Try latin-1
        try:
            df = pd.read_csv(path, nrows=5, encoding="latin-1", on_bad_lines="skip")
            result.update({
                "columns": list(df.columns[:max_cols]),
                "column_count": len(df.columns),
                "encoding": "latin-1",
                "note": "Non-UTF8 encoding",
            })
        except Exception as e:
            result["error"] = f"Cannot parse: {e}"
    except Exception as e:
        result["error"] = f"Parse error: {str(e)[:200]}"

    return result


def _inspect_excel(path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect Excel files."""
    import pandas as pd

    preview_rows = config.get("csv_preview_rows", 10)
    max_cols = config.get("max_columns_display", 30)

    result = {"file_type": "excel"}

    try:
        xls = pd.ExcelFile(path)
        sheet_names = xls.sheet_names
        result["sheet_names"] = sheet_names
        result["sheet_count"] = len(sheet_names)

        # Inspect each sheet (up to 10)
        sheets_info = []
        for sname in sheet_names[:10]:
            try:
                # Read only preview rows to avoid loading huge sheets
                df = pd.read_excel(xls, sheet_name=sname, nrows=preview_rows + 5)
                total_cols = len(df.columns)
                columns = list(df.columns[:max_cols])
                dtypes = {str(c): str(df[c].dtype) for c in columns}

                # Count named vs unnamed columns for header detection
                named_cols = [c for c in columns if not str(c).startswith("Unnamed")]

                sample = df.head(3).to_dict(orient="records")
                # Only keep first max_cols keys in sample
                sample = [{k: v for i, (k, v) in enumerate(row.items()) if i < max_cols} for row in sample]
                for row in sample:
                    for k, v in row.items():
                        s = str(v)
                        if len(s) > 100:
                            row[k] = s[:100] + "..."

                # Estimate total rows without loading full sheet
                # Read a second time with no row limit but only 1 column
                try:
                    df_count = pd.read_excel(xls, sheet_name=sname, usecols=[0])
                    total_rows = len(df_count)
                except Exception:
                    total_rows = len(df)

                sheets_info.append({
                    "sheet_name": sname,
                    "columns": columns,
                    "named_columns": named_cols[:max_cols],
                    "column_count": total_cols,
                    "row_count": total_rows,
                    "dtypes": dtypes,
                    "sample_rows": sample,
                    "has_header": _looks_like_header(columns),
                    "has_numeric_data": any(
                        "float" in str(d) or "int" in str(d) for d in dtypes.values()
                    ),
                })
            except Exception as e:
                sheets_info.append({
                    "sheet_name": sname,
                    "error": str(e)[:200],
                })

        result["sheets"] = sheets_info

    except Exception as e:
        result["error"] = f"Excel parse error: {str(e)[:200]}"

    return result


def _inspect_hdf5(path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect HDF5/NXS files."""
    result = {"file_type": "hdf5"}

    try:
        import h5py

        max_datasets = config.get("h5_max_datasets", 50)

        with h5py.File(path, "r") as f:
            datasets = []
            groups = []

            def _visit(name, obj):
                if len(datasets) >= max_datasets:
                    return
                if isinstance(obj, h5py.Dataset):
                    datasets.append({
                        "path": name,
                        "shape": list(obj.shape),
                        "dtype": str(obj.dtype),
                        "size_elements": int(obj.size) if obj.size else 0,
                    })
                elif isinstance(obj, h5py.Group):
                    groups.append(name)

            f.visititems(_visit)

            result.update({
                "groups": groups[:20],
                "group_count": len(groups),
                "datasets": datasets,
                "dataset_count": len(datasets),
                "root_attrs": dict(f.attrs) if f.attrs else {},
            })

            # Convert numpy types in attrs
            for k, v in result["root_attrs"].items():
                try:
                    result["root_attrs"][k] = str(v)
                except Exception:
                    result["root_attrs"][k] = "<unserializable>"

    except ImportError:
        result["error"] = "h5py not installed"
    except Exception as e:
        result["error"] = f"HDF5 parse error: {str(e)[:200]}"

    return result


def _inspect_json(path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect JSON files."""
    import json as json_mod

    result = {"file_type": "json"}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read(50000)  # Read first 50KB
            data = json_mod.loads(raw if len(raw) < 50000 else raw + "}")

        if isinstance(data, list):
            result["structure"] = "array"
            result["length"] = len(data)
            if data and isinstance(data[0], dict):
                result["keys"] = list(data[0].keys())[:20]
                result["sample"] = str(data[0])[:500]
        elif isinstance(data, dict):
            result["structure"] = "object"
            result["keys"] = list(data.keys())[:20]
            result["sample"] = {
                k: str(v)[:100] for k, v in list(data.items())[:5]
            }

    except Exception as e:
        result["error"] = f"JSON parse error: {str(e)[:200]}"

    return result


def _inspect_numpy(path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect .npy/.npz files."""
    result = {"file_type": "numpy"}

    try:
        import numpy as np

        if path.endswith(".npz"):
            with np.load(path, allow_pickle=False) as data:
                arrays = {}
                for key in list(data.keys())[:20]:
                    arr = data[key]
                    arrays[key] = {
                        "shape": list(arr.shape),
                        "dtype": str(arr.dtype),
                    }
                result["arrays"] = arrays
        else:
            arr = np.load(path, allow_pickle=False)
            result["shape"] = list(arr.shape)
            result["dtype"] = str(arr.dtype)

    except ImportError:
        result["error"] = "numpy not installed"
    except Exception as e:
        result["error"] = f"Numpy parse error: {str(e)[:200]}"

    return result


def _inspect_mat(path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect MATLAB .mat files."""
    result = {"file_type": "matlab"}

    try:
        from scipy.io import loadmat

        data = loadmat(path, squeeze_me=True)
        variables = {}
        for key, val in data.items():
            if key.startswith("_"):
                continue
            try:
                import numpy as np
                if isinstance(val, np.ndarray):
                    variables[key] = {
                        "shape": list(val.shape),
                        "dtype": str(val.dtype),
                    }
                else:
                    variables[key] = {"type": type(val).__name__}
            except Exception:
                variables[key] = {"type": str(type(val))}

        result["variables"] = variables

    except ImportError:
        result["error"] = "scipy not installed"
    except Exception as e:
        result["error"] = f"MAT parse error: {str(e)[:200]}"

    return result


# ===================================================================
# Helpers
# ===================================================================

def _looks_like_header(columns: List[str]) -> bool:
    """Check if column names look like real headers (not auto-generated)."""
    if not columns:
        return False
    # Auto-generated headers are usually 0, 1, 2... or Unnamed: 0, etc.
    auto_patterns = {"0", "1", "2", "3", "4", "5"}
    str_cols = [str(c) for c in columns]
    if all(c in auto_patterns or c.startswith("Unnamed") for c in str_cols):
        return False
    # Real headers usually contain letters
    return any(any(ch.isalpha() for ch in str(c)) for c in columns)


def _get_extension(name: str) -> str:
    """Get file extension."""
    name = name.lower()
    if name.endswith(".tar.gz"):
        return ".tar.gz"
    if name.endswith(".tgz"):
        return ".tgz"
    _, ext = os.path.splitext(name)
    return ext


def _looks_like_documentation(stem: str, fname: str) -> bool:
    lower = fname.lower()
    doc_names = {
        "readme", "license", "licence", "citation", "manifest",
        "metadata", "description", "data_description", "dataset_description",
    }
    doc_tokens = (
        "readme", "metadata", "description", "data-description",
        "dataset-description", "manifest", "codebook", "column", "license",
    )
    if stem in doc_names:
        return True
    return any(token in lower for token in doc_tokens)


def _human_size(nbytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"

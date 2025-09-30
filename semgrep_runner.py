import json
import os
import shutil
import subprocess
import tempfile
from typing import Tuple, List, Dict, Any

import pandas as pd

import config


def _ensure_semgrep_available() -> None:
    semgrep_path = shutil.which("semgrep")
    if semgrep_path is None:
        raise RuntimeError("Semgrep CLI not found. Ensure it is installed in the current environment.")


def _parse_semgrep_json(data: Dict[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    results = data.get("results", [])
    for item in results:
        path = item.get("path")
        start = (item.get("start") or {}).get("line")
        check_id = item.get("check_id")
        extra = item.get("extra") or {}
        message = extra.get("message")
        severity = (extra.get("severity") or "").upper()
        rows.append({"file": path, "line": start, "rule": check_id, "message": message, "severity": severity})
    df = pd.DataFrame(rows, columns=["file", "line", "rule", "message", "severity"])
    return df


def run_semgrep(target_path: str, timeout_seconds: int = 180) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    _ensure_semgrep_available()
    os.environ["SEMGREP_APP_TOKEN"] = getattr(config, "SEMGREP_APP_TOKEN", "")
    cmd = ["semgrep", "--config=auto", "--json", f"--timeout={timeout_seconds}", "--disable-version-check", "--error", target_path]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"Semgrep failed (code {proc.returncode}). Stderr: {proc.stderr.strip()}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse Semgrep JSON output: {exc}. Raw: {proc.stdout[:500]}")
    df = _parse_semgrep_json(data)
    return df, data

import sqlite3
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import pandas as pd

DB_PATH = "users.db"  # reuse same DB file


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_models() -> None:
    conn = get_conn()
    cur = conn.cursor()
    # Projects
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Scans
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            project_id INTEGER,
            target TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            score REAL,
            findings_count INTEGER,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
        """
    )
    # Findings
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            file TEXT,
            line INTEGER,
            rule TEXT,
            message TEXT,
            severity TEXT,
            owasp TEXT,
            recommendation TEXT,
            FOREIGN KEY(scan_id) REFERENCES scans(id)
        )
        """
    )
    conn.commit()
    conn.close()


def get_or_create_project(user: str, name: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM projects WHERE user=? AND name=?", (user, name))
    row = cur.fetchone()
    if row:
        conn.close()
        return int(row["id"])
    cur.execute("INSERT INTO projects(user, name) VALUES(?, ?)", (user, name))
    conn.commit()
    project_id = cur.lastrowid
    conn.close()
    return int(project_id)


def compute_security_score(df: pd.DataFrame) -> float:
    if df is None or df.empty:
        return 100.0
    weights = {"CRITICAL": 30, "HIGH": 20, "MEDIUM": 10, "LOW": 5, "INFO": 2}
    total_penalty = 0
    for _, row in df.iterrows():
        sev = str(row.get("severity", "")).upper()
        total_penalty += weights.get(sev, 5)
    # Normalize: each penalty point reduces score; clamp 0..100
    score = max(0.0, 100.0 - total_penalty)
    return round(score, 2)


def map_rule_to_owasp(rule: Optional[str], message: Optional[str]) -> str:
    text = f"{rule or ''} {message or ''}".lower()
    if any(k in text for k in ["sql", "sqli", "injection"]):
        return "A03:2021 Injection"
    if "xss" in text or "cross-site scripting" in text:
        return "A03:2021 Injection (XSS)"
    if "auth" in text or "jwt" in text or "session" in text:
        return "A07:2021 Identification and Authentication Failures"
    if "path traversal" in text or "directory traversal" in text:
        return "A01:2021 Broken Access Control"
    if "csrf" in text:
        return "A05:2021 Security Misconfiguration"
    return "Unmapped"


def insert_scan_with_findings(
    user: str,
    project_name: str,
    target: str,
    df: pd.DataFrame,
    recommendations: Optional[str] = None,
) -> Tuple[int, float, int]:
    project_id = get_or_create_project(user, project_name)
    score = compute_security_score(df)
    findings_count = 0 if df is None else int(len(df))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO scans(user, project_id, target, score, findings_count) VALUES(?, ?, ?, ?, ?)",
        (user, project_id, target, score, findings_count),
    )
    scan_id = cur.lastrowid

    if df is not None and not df.empty:
        records = []
        for _, r in df.iterrows():
            owasp = map_rule_to_owasp(r.get("rule"), r.get("message"))
            records.append(
                (
                    scan_id,
                    r.get("file"),
                    int(r.get("line")) if pd.notna(r.get("line")) else None,
                    r.get("rule"),
                    r.get("message"),
                    str(r.get("severity") or "").upper(),
                    owasp,
                    recommendations,
                )
            )
        cur.executemany(
            """
            INSERT INTO findings(
                scan_id, file, line, rule, message, severity, owasp, recommendation
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    conn.commit()
    conn.close()
    return int(scan_id), float(score), findings_count


def query_scan_history(
    user: str,
    project: Optional[str] = None,
    severity: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    conn = get_conn()
    params: List[Any] = [user]
    sql = (
        "SELECT s.id as scan_id, s.started_at, s.target, s.score, s.findings_count, p.name as project, "
        "f.file, f.line, f.rule, f.message, f.severity, f.owasp "
        "FROM scans s "
        "LEFT JOIN projects p ON p.id = s.project_id "
        "LEFT JOIN findings f ON f.scan_id = s.id "
        "WHERE s.user = ?"
    )
    if project:
        sql += " AND p.name = ?"
        params.append(project)
    if severity:
        sql += " AND UPPER(f.severity) = ?"
        params.append(severity.upper())
    if start_date:
        sql += " AND s.started_at >= ?"
        params.append(start_date.isoformat())
    if end_date:
        sql += " AND s.started_at <= ?"
        params.append(end_date.isoformat())

    sql += " ORDER BY s.started_at DESC, s.id DESC"
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def list_projects(user: str) -> List[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM projects WHERE user=? ORDER BY created_at DESC", (user,))
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

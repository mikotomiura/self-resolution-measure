"""D2: Li & Coblenz (FSE 2026) debugging tasks, from the paper's Table 4 and Table 5.

Two independent transcriptions must agree cell by cell before anything is computed.
"""

from __future__ import annotations

import csv
from pathlib import Path

from stats import Unit

COLUMNS = ["task_id", "developer_id", "group", "task_time_min", "resolved",
           "documentation", "social_technical", "web_sources", "table4_page", "table5_page"]
TABLE5_COLS = ("documentation", "social_technical", "web_sources")
CONSULT_MODES = ("table5", "table5_plus_text")
CLUSTER_COLUMN = "developer_id"   # config.json d2.cluster
RESOLVED_VALUE = "Y"              # config.json d2.resolved


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"{path}: header {reader.fieldnames} != {COLUMNS}")
        return [dict(r) for r in reader]


def compare(a: list[dict], b: list[dict]) -> list[str]:
    """Every disagreement between two transcriptions, as human-readable strings."""
    diffs = []
    if len(a) != len(b):
        diffs.append(f"row count {len(a)} != {len(b)}")
    for i, (ra, rb) in enumerate(zip(a, b), start=2):
        for col in COLUMNS:
            if ra[col].strip() != rb[col].strip():
                diffs.append(f"line {i} {col}: {ra[col]!r} != {rb[col]!r}")
    return diffs


def read_text_external_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def read_text_external(path: Path) -> set[str]:
    return {r["task_id"] for r in read_text_external_rows(path)}


def consulted(row: dict, mode: str, text_ids: set[str]) -> bool:
    table5 = any(row[c] == "1" for c in TABLE5_COLS)
    if mode == "table5":
        return table5
    return table5 or row["task_id"] in text_ids


def to_units(rows: list[dict], mode: str, text_ids: set[str]) -> list[Unit]:
    return [Unit(cluster=r[CLUSTER_COLUMN], resolved=r["resolved"] == RESOLVED_VALUE,
                 consulted=consulted(r, mode, text_ids)) for r in rows]


def _chk(name, observed, expected) -> dict:
    return {"name": name, "observed": observed, "expected": expected, "ok": observed == expected}


def gate(rows: list[dict], text_ids: set[str], g: dict, text_rows: list[dict] | None = None) -> list[dict]:
    ids = [r["task_id"] for r in rows]
    table5 = {r["task_id"]: any(r[c] == "1" for c in TABLE5_COLS) for r in rows}
    checks = [
        _chk("values: resolved in {Y, N}", all(r["resolved"] in ("Y", "N") for r in rows), True),
        _chk("values: Table 5 flags in {0, 1}", all(r[c] in ("0", "1") for r in rows for c in TABLE5_COLS), True),
        _chk("tasks", len(rows), g["tasks"]),
        _chk("unique task ids", len(set(ids)), g["tasks"]),
        _chk("developers", len({r["developer_id"] for r in rows}), g["developers"]),
        _chk("participant tasks", sum(r["group"] == "participant" for r in rows), g["participants_tasks"]),
        _chk("streamer tasks", sum(r["group"] == "streamer" for r in rows), g["streamer_tasks"]),
        _chk("resolved Y", sum(r["resolved"] == "Y" for r in rows), g["resolved_Y"]),
        _chk("resolved N", sum(r["resolved"] == "N" for r in rows), g["resolved_N"]),
        _chk("unresolved ids (Sec. 4.1 text)", sorted(r["task_id"] for r in rows if r["resolved"] == "N"),
             sorted(g["unresolved_ids"])),
        _chk("Table 5 documentation", sum(r["documentation"] == "1" for r in rows), g["table5_documentation"]),
        _chk("Table 5 social-technical", sum(r["social_technical"] == "1" for r in rows),
             g["table5_social_technical"]),
        _chk("Table 5 web sources", sum(r["web_sources"] == "1" for r in rows), g["table5_web_sources"]),
        _chk("participant minutes (7.8 h)",
             sum(int(r["task_time_min"]) for r in rows if r["group"] == "participant"),
             g["participant_minutes"]["value"]),
        _chk("developer_id is the task_id prefix",
             all(r["task_id"].startswith(r["developer_id"]) for r in rows), True),
        _chk("group matches the id letter",
             all((r["group"] == "participant") == r["task_id"].startswith("P") for r in rows), True),
        _chk("text-described tasks exist in Table 4", sorted(text_ids - set(ids)), []),
    ]
    if text_rows is not None:
        # in_table5 in text_external.csv must agree with the transcription.
        wrong = sorted(r["task_id"] for r in text_rows
                       if r["task_id"] in table5 and (r["in_table5"] == "1") != table5[r["task_id"]])
        checks.append(_chk("text_external in_table5 agrees with Table 5", wrong, []))
        checks.append(_chk("values: text_external in_table5 in {0, 1}",
                           all(r["in_table5"] in ("0", "1") for r in text_rows), True))
    return checks

"""Persistent incident ledger for the Active Defense Node.

Until now the node's only memory was the firewall itself plus a
rotating text log. That had three operational costs:

1. Every repeat webhook for an already-blocked IP still burned a
   VirusTotal lookup (the free tier is rate-limited) before the
   firewall duplicate-check ever ran.
2. If a firewall rule was removed by hand, the next webhook re-blocked
   *and re-alerted the team* — there was no record that this IP had
   already been handled.
3. There was no way to answer "what have we blocked this week?"
   without grepping log files.

This module is the node's memory: an append-only JSONL ledger of every
decision (blocked / skipped_duplicate / aborted_safe / error), a
suppression window so repeat events for a recently blocked IP are
answered from the ledger alone, and a small read API the listener
exposes at ``GET /incidents``.

Standard library only. Appends are line-atomic enough for a
single-node deployment and guarded by a lock because the listener
serves requests on multiple threads (Waitress, threads=8).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

ACTIONS = ("blocked", "skipped_duplicate", "aborted_safe", "error")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class IncidentLedger:
    """Append-only JSONL store of defense decisions, keyed by IP."""

    def __init__(self, path: str | os.PathLike) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._last_blocked: dict[str, datetime] = {}
        self._load_index()

    # ── persistence ─────────────────────────────────────────────────

    def _load_index(self) -> None:
        """Rebuild the in-memory last-blocked index from the file, so
        suppression survives restarts."""
        if not self._path.exists():
            return
        try:
            with self._path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue  # a torn final line must not kill startup
                    if record.get("action") == "blocked":
                        ts = _parse_ts(record.get("ts", ""))
                        if ts is not None:
                            self._last_blocked[record["ip"]] = ts
        except OSError:
            # Ledger unreadable (permissions, race with rotation):
            # start empty rather than refuse to defend.
            self._last_blocked = {}

    def record(self, ip: str, action: str, *, vt_score: Optional[int] = None,
               detail: str = "") -> dict:
        """Append one decision and return the stored record."""
        if action not in ACTIONS:
            raise ValueError(f"unknown action: {action!r}")
        entry = {
            "ts": _now().isoformat(timespec="seconds"),
            "ip": ip,
            "action": action,
            "vt_score": vt_score,
            "detail": detail,
        }
        line = json.dumps(entry)
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
            if action == "blocked":
                self._last_blocked[ip] = _now()
        return entry

    # ── queries ─────────────────────────────────────────────────────

    def was_blocked_within(self, ip: str, window_hours: float) -> bool:
        """True if *ip* was blocked within the suppression window —
        the check that lets repeat webhooks skip VirusTotal and the
        firewall entirely."""
        last = self._last_blocked.get(ip)
        if last is None:
            return False
        return _now() - last < timedelta(hours=window_hours)

    def last_blocked_at(self, ip: str) -> Optional[datetime]:
        return self._last_blocked.get(ip)

    def recent(self, limit: int = 50) -> list[dict]:
        """The newest *limit* records, newest first."""
        if not self._path.exists():
            return []
        try:
            lines = self._path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        records: list[dict] = []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(records) >= limit:
                break
        return records

    def counts(self) -> dict[str, int]:
        """Totals per action across the whole ledger."""
        totals = {action: 0 for action in ACTIONS}
        if not self._path.exists():
            return totals
        try:
            lines = self._path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return totals
        for line in lines:
            try:
                action = json.loads(line).get("action")
            except json.JSONDecodeError:
                continue
            if action in totals:
                totals[action] += 1
        return totals


def _parse_ts(raw: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def ledger_from_env() -> IncidentLedger:
    """Build the listener's ledger from environment configuration.

    ``SIEM_INCIDENTS_PATH`` — ledger file location
    (default: ``incidents.jsonl`` next to this module).
    """
    default = Path(__file__).resolve().parent / "incidents.jsonl"
    return IncidentLedger(os.getenv("SIEM_INCIDENTS_PATH", str(default)))


def dedupe_window_hours() -> float:
    """Suppression window in hours (``SIEM_DEDUPE_WINDOW_HOURS``,
    default 24). Invalid values fall back to the default."""
    try:
        hours = float(os.getenv("SIEM_DEDUPE_WINDOW_HOURS", "24"))
        return hours if hours > 0 else 24.0
    except ValueError:
        return 24.0

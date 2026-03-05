from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class TriggerRecord:
    timestamp: str
    condition: str
    status: str


class ITriggerLogWriter(Protocol):
    def append(self, record: TriggerRecord) -> None: ...


class CsvTriggerLogWriter:
    def __init__(self, path: str | Path, *, keep_last: int = 1000) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.keep_last = int(keep_last)
        if not self.path.exists():
            with self.path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "condition", "status"])
        else:
            self._trim_to_last(self.keep_last)

    def _trim_to_last(self, keep_last: int) -> None:
        keep_last = int(keep_last)
        if keep_last <= 0:
            return

        try:
            rows: list[list[str]] = []
            with self.path.open("r", newline="", encoding="utf-8") as f:
                r = csv.reader(f)
                header = next(r, None)
                if header is None:
                    return
                for row in r:
                    if row:
                        rows.append(row)

            if len(rows) <= keep_last:
                return

            rows = rows[-keep_last:]
            with self.path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "condition", "status"])
                w.writerows(rows)
        except Exception:
            return

    def append(self, record: TriggerRecord) -> None:
        with self.path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([record.timestamp, record.condition, record.status])

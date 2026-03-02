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
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with self.path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "condition", "status"])

    def append(self, record: TriggerRecord) -> None:
        with self.path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([record.timestamp, record.condition, record.status])

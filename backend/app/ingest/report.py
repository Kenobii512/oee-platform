"""Yükleme raporu: kabul/ret/atlanan sayıları + ilk N hata."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LoadReport:
    max_errors: int = 50
    accepted: dict[str, int] = field(default_factory=dict)
    rejected: list[dict] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def add_rejection(self, file: str, row: int, error: str) -> None:
        self.rejected.append({"file": file, "row": row, "error": error})

    def to_dict(self) -> dict:
        return {
            "accepted": dict(self.accepted),
            "rejected_count": len(self.rejected),
            "skipped": list(self.skipped),
            "errors": self.rejected[: self.max_errors],
        }

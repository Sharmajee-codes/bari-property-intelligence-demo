from pathlib import Path

from app.schemas import Snapshot


class SyntheticAdapter:
    def __init__(self, path: Path):
        self.path = path

    def collect(self) -> Snapshot:
        return Snapshot.model_validate_json(self.path.read_text(encoding="utf-8"))

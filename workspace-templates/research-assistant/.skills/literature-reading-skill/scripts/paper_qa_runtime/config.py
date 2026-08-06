from __future__ import annotations

import json
from pathlib import Path

from paper_qa_runtime.schemas import RuntimeConfig


def load_runtime_config(path: str | Path) -> RuntimeConfig:
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Runtime config JSON must be an object")
    payload.pop("prompt_version", None)
    return RuntimeConfig(**payload)

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paper_qa_runtime import PaperQARuntime, RuntimeConfig
from paper_qa_runtime.config import load_runtime_config


def main() -> None:
    parser = argparse.ArgumentParser(prog="paper-qa")
    sub = parser.add_subparsers(dest="command", required=True)
    answer_parser = sub.add_parser("answer", help="Answer a question against one paper markdown")
    answer_parser.add_argument("--paper", required=True, help="Path to paper markdown")
    answer_parser.add_argument("--question", required=True)
    answer_parser.add_argument("--history", default=None, help="Optional JSON history file")
    answer_parser.add_argument("--title", default=None)
    answer_parser.add_argument("--config", default=None, help="Optional JSON runtime config file")
    answer_parser.add_argument("--json", action="store_true", help="Print full JSON response")
    args = parser.parse_args()

    if args.command == "answer":
        config = _load_config(args.config)
        runtime = PaperQARuntime(config)
        history = _load_history(args.history)
        result = runtime.answer(
            paper_md=Path(args.paper).read_text(encoding="utf-8"),
            history=history,
            question=args.question,
            title=args.title,
        )
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(result.answer)


def _load_config(path: str | None) -> RuntimeConfig:
    if not path:
        return RuntimeConfig()
    return load_runtime_config(path)


def _load_history(path: str | None) -> list[dict]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("history JSON must be a list")
    return payload


if __name__ == "__main__":
    main()

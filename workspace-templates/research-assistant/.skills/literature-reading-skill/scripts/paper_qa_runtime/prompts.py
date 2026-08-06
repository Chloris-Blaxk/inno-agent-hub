from __future__ import annotations

from paper_qa_runtime.schemas import AgentName, RuntimeConfig


class PromptStore:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.prompt_dir = config.resolved_prompt_dir
        self._cache: dict[str, str] = {}

    def routing_prompt(self) -> str:
        return self._read("routing/control_agent.md")

    def agent_prompt(self, agent: AgentName) -> str:
        return self._read(f"agents/normal/{agent}_agent.md")

    def _read(self, relative_path: str) -> str:
        if relative_path not in self._cache:
            path = self.prompt_dir / relative_path
            if not path.exists():
                raise FileNotFoundError(f"Prompt file not found: {path}")
            self._cache[relative_path] = path.read_text(encoding="utf-8")
        return self._cache[relative_path]

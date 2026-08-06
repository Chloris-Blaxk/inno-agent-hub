from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from paper_qa_runtime import PaperQARuntime, RuntimeConfig
from paper_qa_runtime.config import load_runtime_config


class AnswerRequest(BaseModel):
    paper_md: str
    question: str
    history: list[dict[str, Any]] = Field(default_factory=list)
    title: str | None = None


def create_app(config: RuntimeConfig | None = None) -> FastAPI:
    runtime = PaperQARuntime(config or _load_config_from_env())
    app = FastAPI(title="Paper QA Runtime")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/paper-qa/answer")
    def answer(request: AnswerRequest) -> dict[str, Any]:
        result = runtime.answer(
            paper_md=request.paper_md,
            history=request.history,
            question=request.question,
            title=request.title,
        )
        return result.to_dict()

    return app


def _load_config_from_env() -> RuntimeConfig:
    config_path = os.getenv("PAPER_QA_CONFIG")
    if config_path:
        return load_runtime_config(config_path)
    return RuntimeConfig()


app = create_app()

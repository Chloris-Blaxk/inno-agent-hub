#!/usr/bin/env python3
"""Shared InnoSpark-235B generator configuration for research-line Skills."""
from __future__ import annotations

import os
from typing import Any


DEFAULT_PROVIDER = "InnoSpark"
DEFAULT_MODEL = "InnoSpark-235B"
DEFAULT_BASE_URL = "https://innospark-api.aiecnu.net/v1"
BASE_URL_ENV = "INNOSPARK_AIECNU_BASE_URL"
API_KEY_ENVS = ("INNOSPARK_AIECNU_API_KEY", "INNOSPARK_API_KEY")
MODEL_ENV = "RESEARCH_EDU_GENERATOR_MODEL"


def education_generator_model() -> str:
    return os.getenv(MODEL_ENV, DEFAULT_MODEL)


def education_generator_base_url() -> str:
    return os.getenv(BASE_URL_ENV, DEFAULT_BASE_URL)


def education_generator_api_key() -> str:
    for key in API_KEY_ENVS:
        value = os.getenv(key)
        if value:
            return value
    return ""


def build_education_generator_runtime(
    *,
    skill_id: str,
    task_intent: str,
    used_for: list[str],
    generation_mode: str,
) -> dict[str, Any]:
    """Return auditable runtime metadata without exposing secrets."""
    return {
        "provider": DEFAULT_PROVIDER,
        "model": education_generator_model(),
        "modelRole": "education_content_generator",
        "skillId": skill_id,
        "taskIntent": task_intent,
        "generationMode": generation_mode,
        "usedFor": used_for,
        "api": {
            "style": "openai-compatible",
            "baseUrlEnv": BASE_URL_ENV,
            "defaultBaseUrl": DEFAULT_BASE_URL,
            "apiKeyEnv": list(API_KEY_ENVS),
            "endpoint": "/chat/completions",
            "configured": bool(education_generator_api_key()),
        },
    }


def build_education_generator_source(record_count: int = 1) -> dict[str, Any]:
    return {
        "sourceId": "innospark-235b-education-generator",
        "sourceName": "InnoSpark-235B 教育专用内容生成模型",
        "sourceType": "model_generator",
        "dataType": "education_content_generation",
        "recordCount": max(int(record_count), 0),
        "authorizationStatus": "model_generated",
        "version": education_generator_model(),
        "limitations": [
            "仅用于教育专用内容生成、重写、摘要或语言化包装；事实、引用和项目数据仍必须由用户材料或授权数据源支撑。",
            "API 密钥通过 INNOSPARK_AIECNU_API_KEY 或 INNOSPARK_API_KEY 注入，输出中不记录密钥。",
        ],
    }


def attach_education_generator_runtime(
    payload: dict[str, Any],
    *,
    skill_id: str,
    task_intent: str,
    used_for: list[str],
    generation_mode: str,
) -> dict[str, Any]:
    runtime = build_education_generator_runtime(
        skill_id=skill_id,
        task_intent=task_intent,
        used_for=used_for,
        generation_mode=generation_mode,
    )
    payload["modelRuntime"] = runtime
    payload.setdefault("handoff", {})["modelRuntime"] = {
        "provider": runtime["provider"],
        "model": runtime["model"],
        "modelRole": runtime["modelRole"],
        "generationMode": runtime["generationMode"],
    }
    metrics = payload.setdefault("qualityReport", {}).setdefault("metrics", {})
    metrics["educationGeneratorModel"] = runtime["model"]
    metrics["educationGeneratorProvider"] = runtime["provider"]
    metrics["educationGeneratorConfigured"] = runtime["api"]["configured"]
    return payload

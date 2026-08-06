from __future__ import annotations

import json
import re

from paper_qa_runtime.llm import ChatClient
from paper_qa_runtime.prompts import PromptStore
from paper_qa_runtime.schemas import AgentName, ChatMessage, RuntimeConfig
from paper_qa_runtime.text_utils import extract_json_object, preview


VALID_AGENTS: set[str] = {"review", "method", "result", "discussion", "general"}


class AgentRouter:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        prompts: PromptStore,
        llm_client: ChatClient,
    ):
        self.config = config
        self.prompts = prompts
        self.llm_client = llm_client

    def route(self, *, title: str, question: str, history: list[ChatMessage]) -> AgentName:
        if self.config.routing_use_llm:
            try:
                raw = self.llm_client.complete(
                    system_prompt=self.prompts.routing_prompt(),
                    context=f"论文标题：{title}",
                    user_message=self._build_user_message(question=question, history=history),
                    history=[],
                    max_tokens=120,
                    temperature=0.0,
                )
                parsed = self._parse_agent(raw)
                if parsed:
                    return parsed
            except Exception:  # noqa: BLE001
                pass
        return heuristic_route(question)

    @staticmethod
    def _build_user_message(*, question: str, history: list[ChatMessage]) -> str:
        recent = []
        for msg in history[-3:]:
            role = "用户" if msg.role == "user" else "AI助手"
            content = preview(msg.content, 240)
            if content:
                recent.append(f"{role}: {content}")
        history_text = "\n".join(recent) if recent else "无"
        return (
            f"最近对话历史：\n{history_text}\n\n"
            f"用户最新问题：{question}\n\n"
            "请分析这个问题应该路由给哪个智能体，并只输出 JSON，例如 "
            '{"agent_name":"method"}。'
        )

    @staticmethod
    def _parse_agent(raw: str) -> AgentName | None:
        try:
            payload = json.loads(extract_json_object(raw))
            agent = str(payload.get("agent_name") or "general").replace("_agent", "")
            if agent == "reject":
                return "general"
            if agent in VALID_AGENTS:
                return agent  # type: ignore[return-value]
        except Exception:  # noqa: BLE001
            pass
        lowered = raw.lower()
        for agent in VALID_AGENTS:
            if agent in lowered:
                return agent  # type: ignore[return-value]
        return None


def heuristic_route(question: str) -> AgentName:
    text = question.lower()
    keyword_map = {
        "method": ("方法", "样本", "数据", "变量", "问卷", "模型", "实验", "measure", "sample"),
        "result": ("结果", "发现", "统计", "显著", "表明", "effect", "finding", "result"),
        "discussion": ("讨论", "结论", "局限", "启示", "展望", "未来", "conclusion", "limitation"),
        "review": ("背景", "引言", "综述", "研究问题", "理论", "文献", "background", "review"),
    }
    for agent, keywords in keyword_map.items():
        if any(keyword in text for keyword in keywords):
            return agent  # type: ignore[return-value]
    if re.search(r"(主要|核心|讲了什么|是什么|总结|概括)", question):
        return "review"
    return "general"

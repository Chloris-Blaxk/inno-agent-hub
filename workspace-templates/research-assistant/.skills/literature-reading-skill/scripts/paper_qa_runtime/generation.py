from __future__ import annotations

from paper_qa_runtime.llm import ChatClient
from paper_qa_runtime.prompts import PromptStore
from paper_qa_runtime.schemas import AgentName, ChatMessage, RuntimeConfig


class AnswerGenerator:
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

    def generate(
        self,
        *,
        agent: AgentName,
        context: str,
        question: str,
        history: list[ChatMessage],
    ) -> str:
        prompt = self.prompts.agent_prompt(agent)
        return self.llm_client.complete(
            system_prompt=prompt,
            context=context,
            user_message=question,
            history=history,
            max_tokens=self.config.llm_max_tokens,
            temperature=self.config.llm_temperature,
        )

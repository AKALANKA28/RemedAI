from __future__ import annotations

import json
from typing import Any, TypeVar

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel

from backend.app.core.config import settings

T = TypeVar('T', bound=BaseModel)


def build_chat_model() -> ChatOllama:
    """Create the local Ollama chat model used by all agents."""
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=settings.ollama_temperature,
        num_ctx=32768,
    )


class StructuredLLM:
    """Ask a local Ollama model for JSON that matches a Pydantic schema."""

    def __init__(self, system_prompt: str, output_model: type[T]):
        self.system_prompt = system_prompt
        self.output_model = output_model
        self.parser = PydanticOutputParser(pydantic_object=output_model)
        self.llm = build_chat_model()
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    'system',
                    '{system_prompt}\n\n'
                    'Return valid JSON only.\n'
                    '{format_instructions}',
                ),
                (
                    'human',
                    'Task:\n{task}\n\n'
                    'Context JSON:\n{context_json}',
                ),
            ]
        )

    def invoke(self, task: str, context: dict[str, Any]) -> T:
        chain = self.prompt | self.llm
        message = chain.invoke(
            {
                'system_prompt': self.system_prompt,
                'format_instructions': self.parser.get_format_instructions(),
                'task': task,
                'context_json': json.dumps(context, ensure_ascii=False, indent=2),
            }
        )
        text = getattr(message, 'content', str(message))
        return self.parser.parse(text)

from __future__ import annotations

import json
from typing import Any, TypeVar

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.services.logging_utils import get_app_logger

T = TypeVar('T', bound=BaseModel)
logger = get_app_logger('llm')


class ModelInvocationError(RuntimeError):
    def __init__(self, agent_name: str, model_name: str, message: str):
        self.agent_name = agent_name
        self.model_name = model_name
        super().__init__(message)


def build_chat_model(model: str | None = None) -> ChatOllama:
    """Create a local Ollama chat model for a specific agent."""
    return ChatOllama(
        model=model or settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=settings.ollama_temperature,
        num_ctx=settings.ollama_context_length,
        keep_alive=settings.ollama_keep_alive,
    )


class StructuredLLM:
    """Ask a local Ollama model for JSON that matches a Pydantic schema."""

    def __init__(self, system_prompt: str, output_model: type[T], agent_name: str = 'default'):
        self.system_prompt = system_prompt
        self.output_model = output_model
        self.agent_name = agent_name
        self.model_name = settings.model_for_agent(agent_name)
        self.parser = PydanticOutputParser(pydantic_object=output_model)
        self.llm = build_chat_model(self.model_name)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    'system',
                    '{system_prompt}\n\n'
                    'Assigned local model: {model_name}\n'
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
        context_json = json.dumps(context, ensure_ascii=False, indent=2)
        candidates = [self.model_name]
        for fallback in settings.ollama_fallback_models:
            if fallback not in candidates:
                candidates.append(fallback)
        last_exc: Exception | None = None

        for model_name in candidates:
            llm = build_chat_model(model_name)
            chain = self.prompt | llm
            logger.info(
                'LLM start agent=%s model=%s context_chars=%s task=%s',
                self.agent_name,
                model_name,
                len(context_json),
                task,
            )
            try:
                message = chain.invoke(
                    {
                        'system_prompt': self.system_prompt,
                        'format_instructions': self.parser.get_format_instructions(),
                        'model_name': model_name,
                        'task': task,
                        'context_json': context_json,
                    }
                )
                text = getattr(message, 'content', str(message))
                parsed = self.parser.parse(text)
                if model_name != self.model_name:
                    logger.warning('LLM fallback success agent=%s model=%s', self.agent_name, model_name)
                    self.model_name = model_name
                    self.llm = llm
                else:
                    logger.info('LLM success agent=%s model=%s', self.agent_name, model_name)
                return parsed
            except Exception as exc:
                last_exc = exc
                logger.exception('LLM failed agent=%s model=%s error=%s', self.agent_name, model_name, exc)

        raise ModelInvocationError(self.agent_name, self.model_name, str(last_exc) if last_exc else 'LLM failed')

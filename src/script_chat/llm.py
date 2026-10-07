import os
import time
from typing import TypeVar

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import BaseModel

from src.core.metrics import (
    SCRIPT_CHAT_LLM_REQUESTS_TOTAL,
    SCRIPT_CHAT_LLM_DURATION_SECONDS,
    SCRIPT_CHAT_LLM_TOKENS_TOTAL,
)


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class ScriptChatLLMError(RuntimeError):
    pass


def get_openai_llm(model: str, temperature: float = 0.2, tools: list[dict] | None = None):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ScriptChatLLMError("OPENAI_API_KEY not found")

    llm = ChatOpenAI(model=model, temperature=temperature, api_key=api_key)
    return llm.bind_tools(tools) if tools else llm


def invoke_structured(
    messages: list[BaseMessage],
    schema: type[StructuredModel],
    *,
    model: str = "gpt-5.4-mini",
    temperature: float = 0.2,
) -> StructuredModel:
    t0 = time.perf_counter()
    status = "success"
    try:
        llm = get_openai_llm(model=model, temperature=temperature)
        structured_llm = llm.with_structured_output(schema)
        result = structured_llm.invoke(messages)
        if result is None:
            status = "error"
            raise ScriptChatLLMError("LLM returned no structured result")
        return result
    except Exception:
        status = "error"
        raise
    finally:
        elapsed = time.perf_counter() - t0
        SCRIPT_CHAT_LLM_REQUESTS_TOTAL.labels(model=model, call_type="structured", status=status).inc()
        SCRIPT_CHAT_LLM_DURATION_SECONDS.labels(model=model, call_type="structured").observe(elapsed)


def _message_content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def _responses_input_from_messages(messages: list[BaseMessage]) -> tuple[str | None, list[dict]]:
    instructions = []
    input_messages = []

    for message in messages:
        content = _message_content_to_text(getattr(message, "content", ""))
        message_type = getattr(message, "type", "")

        if message_type == "system":
            instructions.append(content)
        elif message_type in {"ai", "assistant"}:
            input_messages.append({"role": "assistant", "content": content})
        else:
            input_messages.append({"role": "user", "content": content})

    return ("\n\n".join(instructions) if instructions else None, input_messages)


def invoke_structured_with_responses_tools(
    messages: list[BaseMessage],
    schema: type[StructuredModel],
    *,
    model: str = "gpt-5.4-mini",
    temperature: float = 0.2,
    tools: list[dict] | None = None,
    max_tool_calls: int | None = None,
) -> StructuredModel:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ScriptChatLLMError("OPENAI_API_KEY not found")

    instructions, input_messages = _responses_input_from_messages(messages)
    client = OpenAI(api_key=api_key)
    t0 = time.perf_counter()
    status = "success"
    try:
        response = client.responses.parse(
            model=model,
            instructions=instructions,
            input=input_messages,
            text_format=schema,
            tools=tools or [],
            max_tool_calls=max_tool_calls,
            temperature=temperature,
        )
        if response.output_parsed is None:
            status = "error"
            raise ScriptChatLLMError("LLM returned no structured result")

        if hasattr(response, "usage") and response.usage:
            SCRIPT_CHAT_LLM_TOKENS_TOTAL.labels(model=model, token_type="prompt").inc(response.usage.prompt_tokens or 0)
            SCRIPT_CHAT_LLM_TOKENS_TOTAL.labels(model=model, token_type="completion").inc(response.usage.completion_tokens or 0)

        return response.output_parsed
    except Exception:
        status = "error"
        raise
    finally:
        elapsed = time.perf_counter() - t0
        SCRIPT_CHAT_LLM_REQUESTS_TOTAL.labels(model=model, call_type="responses_tools", status=status).inc()
        SCRIPT_CHAT_LLM_DURATION_SECONDS.labels(model=model, call_type="responses_tools").observe(elapsed)


def invoke_text(
    messages: list[BaseMessage],
    *,
    model: str = "gpt-5.4-mini",
    temperature: float = 0.2,
    tools: list[dict] | None = None,
) -> str:
    t0 = time.perf_counter()
    status = "success"
    try:
        response = get_openai_llm(model=model, temperature=temperature, tools=tools).invoke(messages)
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            SCRIPT_CHAT_LLM_TOKENS_TOTAL.labels(model=model, token_type="prompt").inc(response.usage_metadata.get("input_tokens", 0))
            SCRIPT_CHAT_LLM_TOKENS_TOTAL.labels(model=model, token_type="completion").inc(response.usage_metadata.get("output_tokens", 0))

        content = response.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            return "".join(parts).strip()
        return str(content).strip()
    except Exception:
        status = "error"
        raise
    finally:
        elapsed = time.perf_counter() - t0
        SCRIPT_CHAT_LLM_REQUESTS_TOTAL.labels(model=model, call_type="text", status=status).inc()
        SCRIPT_CHAT_LLM_DURATION_SECONDS.labels(model=model, call_type="text").observe(elapsed)

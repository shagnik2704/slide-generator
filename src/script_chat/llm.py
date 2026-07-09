import os
from typing import TypeVar

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import BaseModel


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
    llm = get_openai_llm(model=model, temperature=temperature)
    structured_llm = llm.with_structured_output(schema)
    result = structured_llm.invoke(messages)
    if result is None:
        raise ScriptChatLLMError("LLM returned no structured result")
    return result


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
        raise ScriptChatLLMError("LLM returned no structured result")
    return response.output_parsed


def invoke_text(
    messages: list[BaseMessage],
    *,
    model: str = "gpt-5.4-mini",
    temperature: float = 0.2,
    tools: list[dict] | None = None,
) -> str:
    response = get_openai_llm(model=model, temperature=temperature, tools=tools).invoke(messages)
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

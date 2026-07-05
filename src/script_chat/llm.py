import os
from typing import TypeVar

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
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

"""LLM utility functions for outline chat."""
import os
import json
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI
import requests

# Load .env from project root (5 levels up from this file: outline_chat -> routes -> api -> src -> root)
project_root = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")


def generate_llm_text(
    prompt: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    system_prompt: str = "You are a helpful assistant used inside a Spoken Tutorial course outline creation system.",
) -> str:
    """
    Generate text using OpenAI chat completions.

    This route must use ONLY OpenAI (no Gemini / Google GenAI).
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


def friendly_rewrite_question(base_question: str, outline_type: str, phase: str) -> str:
    """
    Use OpenAI to lightly rewrite a base question in a more friendly,
    conversational tone while keeping the meaning the same.
    Falls back to the original question on any error.
    Ensures the final question is under 100 characters.
    """
    try:
        prompt = f"""You are a warm, supportive assistant helping to interview a subject-matter expert for a Spoken Tutorial course outline.

Rewrite the following question in a more friendly, conversational way, but keep the meaning and structure the same.

Guidelines:
- Address the user as "you".
- Sound encouraging and collaborative (as if you are gently guiding them).
- Keep it within 1–2 sentences.
- Do NOT add extra instructions, tips, examples, or emojis beyond what is already present.
- Do NOT change any technical terms or placeholders.
- CRITICAL: The final question MUST be under 100 characters. If needed, shorten it while keeping essential information.

Question:
{base_question}

Return ONLY the rewritten question text (under 100 characters)."""

        rewritten = generate_llm_text(
            prompt,
            temperature=0.4,
            max_tokens=128,  # Reduced to encourage shorter output
            system_prompt="You are a warm but precise rewriting assistant. Always keep questions under 100 characters.",
        )
        if len(rewritten.strip()) < 5:
            return base_question
        
        rewritten = rewritten.strip()
        
        # Enforce 100 character limit - truncate if needed
        if len(rewritten) > 100:
            # Try to truncate at a sentence boundary or word boundary
            truncated = rewritten[:97] + "..."
            # If the original base question is shorter, use it instead
            if len(base_question) <= 100:
                return base_question
            return truncated
        
        return rewritten
    except Exception:
        # Fallback: if base question is already under 100 chars, return it
        if len(base_question) <= 100:
            return base_question
        # Otherwise truncate base question
        return base_question[:97] + "..."


def get_example_answer_hint(
    outline_type: str,
    phase: str,
    base_question: str,
) -> str | None:
    """
    Use the LLM to generate a short, concrete example answer for the given question.

    The example is conditioned on:
    - the outline type (FOSS / ICT),
    - the current phase (warmup / outcomes / examples / structure / metadata),
    - and the exact question text.
    """
    outline_type = outline_type.upper()

    try:
        prompt = f"""You are helping a subject-matter expert fill a Spoken Tutorial course outline via chat.

Your task: given ONE question we are asking the user, write ONE SHORT, CONCRETE example answer that fits that question.

Guidelines:
- Answer as if you are the SME giving a good, realistic response.
- Keep it to a single line or a very short paragraph.
- Do NOT include explanations, meta-commentary, or phrases like "for example" or "you could say".
- Do NOT repeat the question text.
- Only return the example answer text itself.
- If the question is asking for a course name, outline name, tutorial title, or similar short title, make sure your answer is under 50 characters and uses only letters, numbers, and spaces (no special characters).

Context:
- Outline type: {outline_type}
- Phase: {phase}
- Question: {base_question}

Now return just ONE example answer that would be appropriate for this question."""

        example = generate_llm_text(
            prompt,
            temperature=0.4,
            max_tokens=128,
            system_prompt="You generate only short, concrete example answers for course-outline questions.",
        ).strip()

        # Basic sanity check – avoid empty or obviously long essays
        if not example or len(example) < 5 or len(example) > 400:
            return None

        return example
    except Exception:
        return None


def web_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Perform a web search using DuckDuckGo and return results.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return
        
    Returns:
        List of dictionaries with 'title', 'url', and 'snippet' keys
    """
    results = []
    
    try:
        # Try DuckDuckGo Instant Answer API first
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Get abstract if available
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", "DuckDuckGo Result"),
                "url": data.get("AbstractURL", ""),
                "snippet": data.get("AbstractText", "")
            })
        
        # Get Answer if available
        if data.get("Answer") and len(results) < max_results:
            results.append({
                "title": "Answer",
                "url": data.get("AbstractURL", ""),
                "snippet": data.get("Answer", "")
            })
        
        # Get Definition if available
        if data.get("Definition") and len(results) < max_results:
            results.append({
                "title": data.get("Heading", "Definition"),
                "url": data.get("AbstractURL", ""),
                "snippet": data.get("Definition", "")
            })
        
        # Get related topics
        for topic in data.get("RelatedTopics", []):
            if len(results) >= max_results:
                break
            if isinstance(topic, dict) and "Text" in topic:
                title = "Related Topic"
                if topic.get("FirstURL"):
                    # Extract title from URL
                    url_parts = topic.get("FirstURL", "").split("/")
                    if url_parts:
                        title = url_parts[-1].replace("_", " ").replace("-", " ").title()
                
                results.append({
                    "title": title,
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", "")
                })
        
        # If we still don't have enough results, try Tavily API if available
        if len(results) < max_results:
            tavily_api_key = os.getenv("TAVILY_API_KEY")
            if tavily_api_key:
                try:
                    tavily_url = "https://api.tavily.com/search"
                    tavily_params = {
                        "api_key": tavily_api_key,
                        "query": query,
                        "max_results": max_results - len(results),
                        "search_depth": "basic"
                    }
                    tavily_response = requests.post(tavily_url, json=tavily_params, timeout=10)
                    tavily_response.raise_for_status()
                    tavily_data = tavily_response.json()
                    
                    for result in tavily_data.get("results", []):
                        if len(results) >= max_results:
                            break
                        results.append({
                            "title": result.get("title", "Search Result"),
                            "url": result.get("url", ""),
                            "snippet": result.get("content", "")
                        })
                except Exception:
                    pass
        
    except Exception as e:
        # If all searches fail, return empty results
        # The LLM will still be able to answer based on its training data
        pass
    
    return results[:max_results]


def generate_llm_text_with_tools(
    prompt: str,
    *,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    system_prompt: str = "You are a helpful AI assistant. Answer questions clearly and concisely. Be friendly and professional. When you need current information, use the web_search tool.",
    use_web_search: bool = True,
) -> str:
    """
    Generate text using OpenAI chat completions with function calling for web search.
    
    This function allows the model to search the web when it needs current information.
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=openai_api_key)
    
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]
    
    # Define web search tool
    tools = []
    if use_web_search:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for current information, news, facts, or any up-to-date data. Use this when the user asks about recent events, current information, or anything that might have changed recently.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to find information on the web"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of search results to return (default: 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    # First call - let model decide if it needs to search
    # Use gpt-4o-mini for better function calling support
    model_name = "gpt-4o-mini"
    
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools if tools else None,
        tool_choice="auto" if tools else None,
    )
    
    message = response.choices[0].message
    
    # If the model wants to use a tool, execute it
    if message.tool_calls:
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name == "web_search":
                # Execute web search
                search_results = web_search(
                    query=function_args.get("query", ""),
                    max_results=function_args.get("max_results", 5)
                )
                
                # Add tool result to messages
                messages.append(message)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({
                        "results": search_results,
                        "count": len(search_results)
                    })
                })
        
        # Second call - model generates final answer with search results
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip()
    
    # No tool calls needed, return direct response
    return (message.content or "").strip()


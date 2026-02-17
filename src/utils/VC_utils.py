from langchain_google_genai import ChatGoogleGenerativeAI
from tavily import TavilyClient
import os
from dotenv import load_dotenv 
load_dotenv()
from langchain_openai import ChatOpenAI
from langchain.tools import tool

# Semaphore configuration for concurrent operations
SEMAPHORE_CONFIG = {
    "extraction": 8,    # HTTP is cheap, concurrent parsing is safe
    "update": 3,        # LLM + search_tool is expensive and rate-limited
    "split": 4          # Pure LLM, moderate usage
}

# Lazy-loaded instances to prevent import-time failures
_llm_openrouter = None
_llm_openai = None
_llm_gemini = None
_search_client = None


def get_llm_openrouter():
    """Lazily initialize OpenRouter LLM."""
    global _llm_openrouter
    if _llm_openrouter is None:
        _llm_openrouter = ChatOpenAI(
            model="xiaomi/mimo-v2-flash:free",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
    return _llm_openrouter


def get_llm_openai():
    """Lazily initialize OpenAI LLM."""
    global _llm_openai
    if _llm_openai is None:
        _llm_openai = ChatOpenAI(
            model="gpt-5.2",
            api_key=os.getenv("OPENAI_API_KEY")
        )
    return _llm_openai


def get_llm_gemini():
    """Lazily initialize Google Gemini LLM."""
    global _llm_gemini
    if _llm_gemini is None:
        _llm_gemini = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            google_api_key=os.getenv("GEMINI_KEY")  # Fixed: use google_api_key
        )
    return _llm_gemini


def get_search_client():
    """Lazily initialize Tavily search client."""
    global _search_client
    if _search_client is None:
        _search_client = TavilyClient(api_key=os.getenv("TAVILY_KEY"))
    return _search_client


# Lazy wrapper for backward compatibility with code that imports `llm`
class _LazyLLM:
    """Wrapper that lazily initializes the LLM on first use."""
    _instance = None
    
    def __getattr__(self, name):
        if _LazyLLM._instance is None:
            _LazyLLM._instance = get_llm_gemini()
        return getattr(_LazyLLM._instance, name)
    
    def __call__(self, *args, **kwargs):
        if _LazyLLM._instance is None:
            _LazyLLM._instance = get_llm_gemini()
        return _LazyLLM._instance(*args, **kwargs)
    
    def invoke(self, *args, **kwargs):
        if _LazyLLM._instance is None:
            _LazyLLM._instance = get_llm_gemini()
        return _LazyLLM._instance.invoke(*args, **kwargs)
    
    def bind_tools(self, *args, **kwargs):
        if _LazyLLM._instance is None:
            _LazyLLM._instance = get_llm_gemini()
        return _LazyLLM._instance.bind_tools(*args, **kwargs)


# This is now lazy - won't crash at import time
llm = _LazyLLM()


@tool
def search_tool(query: str):
    """Search the web for latest software updates."""
    return get_search_client().search(query=query, max_results=3, topic='general')


template_url = "https://docs.google.com/spreadsheets/d/1H6Pzc3h5j8VfO7IBLvNXX8Qo6UpZHo4PnIhWggeIPMM/edit?usp=sharing"
template_id = template_url.split('/')[5]
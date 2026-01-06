from langchain_google_genai import ChatGoogleGenerativeAI
from tavily import TavilyClient
import os
from dotenv import load_dotenv 
load_dotenv()
from langchain_openai import ChatOpenAI
from langchain.tools import tool

llm_openRouter = ChatOpenAI(
    model="xiaomi/mimo-v2-flash:free",  # Specify a model available on OpenRouter
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

llm_openai = ChatOpenAI(
    model ="gpt-5.2",
    api_key=os.getenv("OPENAI_API_KEY")
)

llm_gemini = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    api_key=os.getenv("GEMINI_KEY")
)

llm = llm_openai 
# llm = llm_openRouter
# llm = llm_gemini

search_client = TavilyClient(api_key=os.getenv("TAVILY_KEY"))
@tool
def search_tool(query:str):
    """Search the web for latest software updates."""
    return search_client.search(query=query,max_results=3,topic='general')


template_url = "https://docs.google.com/spreadsheets/d/1soF2643TAWM91p9Xv_jB-VSgRil99-SSujGX0I_ipyU/edit?gid=0#gid=0"
template_id = template_url.split('/')[5]


# gcloud auth application-default login --scopes=https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/cloud-platform
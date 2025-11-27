from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

try:
    llm = ChatGoogleGenerativeAI(model="gemini-pro")
    response = llm.invoke("Hello, are you working?")
    print(f"Response: {response.content}")
except Exception as e:
    print(f"Error: {e}")

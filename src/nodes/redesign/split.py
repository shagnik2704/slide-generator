from typing import List
import json
from src.nodes.redesign.utils.schema import TutorialState, SplitedTutorialList
from src.nodes.redesign.utils.config import llm
from src.nodes.redesign.utils.prompts import SPLIT_AGENT_PROMPT3
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", SPLIT_AGENT_PROMPT3),
    ("placeholder", "{messages}")
])


agent = create_react_agent(
    model=llm,
    prompt=prompt,
    tools=[],
    response_format=SplitedTutorialList
)

def duration_split(state: TutorialState) -> TutorialState:

    number_of_tutorials = round(state.old_tutorial.duration / 210)  # Assuming 4 minutes (210 seconds) per tutorial

    payload = {
        "updated_subtopics": state.updated_tutorial.updated_subtopics,
        "duration" : state.old_tutorial.duration,
        "number_of_tutorials": number_of_tutorials
    } 

    response = agent.invoke({"messages": [{"role": "user", "content": json.dumps(payload)}]})
    parsed = response["structured_response"].tutorials
    
    state.splited_tutorial = parsed

    return state
    
    
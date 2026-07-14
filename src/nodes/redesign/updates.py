from src.nodes.redesign.utils.config import search_long_query
from src.nodes.redesign.utils.schema import UpdatedTutorial, TutorialState
from src.nodes.redesign.utils.config import llm, search_long_query
from src.nodes.redesign.utils.prompts import UPDATE_AGENT_PROMPT1
import json
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", UPDATE_AGENT_PROMPT1),
    ("placeholder", "{messages}")
])

agent = create_react_agent(
    model=llm,
    tools=[search_long_query],
    prompt=prompt,
    response_format=UpdatedTutorial
)

def tech_intelligence_agent(state: TutorialState) -> TutorialState:

    payload = {
        "old_tutorial_subtopics": state.old_tutorial.outline
    }
    response = agent.invoke({"messages": [{"role": "user", "content": json.dumps(payload)}]})
    parsed = UpdatedTutorial.model_validate(response["structured_response"])

    state.updated_tutorial = UpdatedTutorial(
        updated_subtopics = parsed.updated_subtopics,
        logs = parsed.logs
    )
    return state

    # if "```json" in response:
    #         raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            
    #     parsed = json.loads(raw_content)
        # Parse the search result to extract updates
        # Here we simulate the extraction process
        
        # parsed = json.loads(search_result["messages"][-1].content) #[-1]["text"])
        
        # updates = {
        #     "updated_title": f"{parsed['updated_title']}(Updated)" if parsed['updated_title'] else tutorial['title'],
        #     "updated_subtopics": (parsed["updated_subtopics"] if parsed['updated_subtopics'] else tutorial['subtopics'])
   
    # return state['tech_updates']
    
    # return search_result
    

# state = {'legacy_raw_data': 'https://spoken-tutorial.org/watch/Linux+AWK/Overview+of+Linux+AWK/English/', 'structured_legacy': [{'title': 'Overview of Linux AWK', 'subtopics': 'About awk commands, AWK Process, Glimpse of Spoken Tutorials available on AWK', 'duation': '00:08:20'}, {'title': 'Basics of awk', 'subtopics': 'Awk Preliminaries, Selection criteria, action, Formatted printing - printf, Fields and -F option, Regular expressions, NR - number of records, Variables', 'duation': '00:08:19'}], 'tech_updates': [], 'final_table': {}, 'errors': []}
# state = DSpace_state
# result = tech_intelligence_agent(state)

# print (result)

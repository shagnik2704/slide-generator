from state import AgentState
from utils import llm_openRouter, search_tool
from langchain.agents import create_agent
import json


agent = create_agent(llm_openRouter,
                     tools=[search_tool],
                     system_prompt='''
                     You are a tech intelligence agent that provides the latest updates on version changes and modificaions on topics based on user queries.
                     Use the search tool to find relevant and recent information.
                     You are given tutorial title and subtopics. Return latest stable version name in updated title and version updates corresponding to the subtopics in updated subtopics.
                     Maintain a log by clearly highlighting what changes are made from older version to newer version. Make an entry only when there is some change.
                     If you cannot find newer updates, tag the older subtopics as 'deprecated' in the log, and if possible find an alternative and present it in one line.
                     Return the output in the JSON format:
                        {
                            "updated_title": "<updated title or same title if no change>" <return type: str>,
                            "updated_subtopics": "<updated subtopics with desired version changes>" <return type: str>
                            "logs": "<List of updates numbered sequentially>" <return type: List>
                        }
                    Follow the format strictly.
                    Return only the resultant JSON and nothing else.
                    ''')
def tech_intelligence_agent(state: AgentState):
#     # This agent would ideally use a search tool. 
#     # Here, it provides a mapping for Linux 24.04 features.

    for i,tutorial in enumerate(state['structured_legacy']):
        print (f"Updating contents regarding version changes: {i+1}/{len(state['structured_legacy'])}")
        query = f"Find the latest stable version updates for the tutorial titled '{tutorial['title']}' with subtopics {tutorial['subtopics']} and maintain a log registering the changes in points."
        search_result = agent.invoke({"messages": [{"role": "user", "content": query}]})
        
        # raw_content = (search_result['messages'][-1].content[-1]['text'])     # use when using gemini
        raw_content = (search_result['messages'][-1].content)                   # use when using openRouter
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            
        parsed = json.loads(raw_content)
        # Parse the search result to extract updates
        # Here we simulate the extraction process
        
        # parsed = json.loads(search_result["messages"][-1].content) #[-1]["text"])
        
        # updates = {
        #     "updated_title": f"{parsed['updated_title']}(Updated)" if parsed['updated_title'] else tutorial['title'],
        #     "updated_subtopics": (parsed["updated_subtopics"] if parsed['updated_subtopics'] else tutorial['subtopics'])
        # }
        state['tech_updates'].append(parsed)
   
    return state
    # return state['tech_updates']
    
    # return search_result
    

# state = {'legacy_raw_data': 'https://spoken-tutorial.org/watch/Linux+AWK/Overview+of+Linux+AWK/English/', 'structured_legacy': [{'title': 'Overview of Linux AWK', 'subtopics': 'About awk commands, AWK Process, Glimpse of Spoken Tutorials available on AWK', 'duation': '00:08:20'}, {'title': 'Basics of awk', 'subtopics': 'Awk Preliminaries, Selection criteria, action, Formatted printing - printf, Fields and -F option, Regular expressions, NR - number of records, Variables', 'duation': '00:08:19'}], 'tech_updates': [], 'final_table': {}, 'errors': []}
# state = DSpace_state
# result = tech_intelligence_agent(state)

# print (result)

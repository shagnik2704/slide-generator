from utils import llm_openRouter
from langchain.agents import create_agent
from state import AgentState
import json

split_agent = create_agent(llm_openRouter,
                           system_prompt="""
                           You are an expert instructional design agent.
                           Your are given an old tutorial with its total duration and new updated tutorials with their subtopics.
                           Your task is to split the new updated tutorial subtopics into fragments of 3-4 minutes tutorials such that to overall duration is comparable to the old tutorial.
                           You may club few subtopics into one tutorial as required.
                           Do not modify the logs or change its return type.
                           Return the output in the format as follows:
                                [
                                    {"tutorial_title":"<relevant title covering subtopics>"
                                     "subtopic":"<splitted fragment from subtopic>",
                                     "estimated_duration":"<new estimated duration (3-4 min)>"
                                    },
                                    {"tutorial_title":"<relevant title covering subtopics>"
                                     "subtopic":"<splitted fragment from subtopic>",
                                     "estimated_duration":"<new estimated duration (3-4 min)>"
                                    },
                                    ...
                                ]
                                Follow the format strictly.
                                Return only the resultant JSON and nothing else.                                                                    
                           """
                        )

def duration_split(state: AgentState):
    
    for i,tutorial in enumerate(state['tech_updates']):
        print (f"Splitting tutorials into smaller fragments: {i+1}/{len(state['tech_updates'])}")
        task = f"Split the given tutorial with total duration of {state['structured_legacy'][i]['duation']} into fragments of 3-4 minutes tutorials delivering subtopics: {tutorial['updated_subtopics']}."
        result = split_agent.invoke({"messages": [{"role": "user", "content": task}]})
        
        # raw_content = (search_result['messages'][-1].content[-1]['text'])     # use when using gemini
        raw_content = (result['messages'][-1].content)                   # use when using openRouter
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            
        parsed = json.loads(raw_content)
        
        tutorial['updated_subtopics'] = parsed
        
    return state
    
    
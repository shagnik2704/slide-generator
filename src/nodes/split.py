from src.utils.VC_utils import llm
from langchain.schema import SystemMessage
from src.core.state import VCAgentState
import json

from langchain.schema import SystemMessage, HumanMessage

PROMPT1 = '''
        You are an expert instructional design agent.

        You will be given:
        1. An OLD tutorial with:
        - tutorial title
        - total duration (in minutes)
        2. A NEW updated tutorial with:
        - tutorial title
        - a list of subtopics

        Your task is to split the NEW updated tutorial subtopics into multiple short tutorial fragments.

        Follow these rules STRICTLY:

        RULES:
        1. Split ONLY if the OLD tutorial duration is GREATER than 4 minutes.
        - If the old duration is ≤ 4 minutes, DO NOT split and return a single tutorial entry.
        2. Each split tutorial must have an estimated duration between **3 and 4 minutes only**.
        3. The number of split tutorials must be the **nearest integer** to:
            (old_tutorial_duration ÷ 3)
        4. The **total sum of estimated durations** of all split tutorials must be **comparable to the old tutorial duration** (small rounding differences are acceptable).
        5. You may club multiple related subtopics into one tutorial fragment when required.
        6. Do NOT invent new concepts; use ONLY the provided subtopics.
        7. Do NOT modify, remove, or reinterpret any logs or metadata.
        8. Do NOT change the return type or output structure.
        9. Ensure titles are concise and clearly represent the covered subtopics.

        OUTPUT FORMAT (STRICT):
        - Return ONLY a valid JSON array.
        - Do NOT include explanations, comments, markdown, or extra text.

        Each JSON object MUST follow this exact structure:

        [
        {
            "tutorial_title": "<relevant title covering subtopics>",
            "subtopic": "<splitted fragment from subtopic>",
            "estimated_duration": "<duration between 3-4 minutes>"
        },
        {
            "tutorial_title": "<relevant title covering subtopics>",
            "subtopic": "<splitted fragment from subtopic>",
            "estimated_duration": "<duration between 3-4 minutes>"
        }
        ]

        IMPORTANT CONSTRAINTS:
        - The JSON must be syntactically valid.
        - All estimated_duration values must be strings.
        - Output ONLY the resultant JSON and NOTHING ELSE.
'''

PROMPT2 = """
            You are an expert instructional design agent.
            Your are given an old tutorial with its total duration and new updated tutorials with their subtopics.
            Your task is to split the new updated tutorial subtopics into fragments of 3-4 minutes tutorials with rules given below:
             1. Split only tutorials greater than 4 minutes. If the old duration is ≤ 4 minutes, DO NOT split and return a single tutorial entry.
             2. The number of split tutorials must be the **nearest integer** to:
                (old_tutorial_duration ÷ 3)
             3. The **total sum of estimated durations** of all split tutorials must be **comparable to the old tutorial duration** (small rounding differences are acceptable).
             4. You may club few subtopics into one tutorial as required.
             5. Do not modify the logs or change its return type.
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

SYSTEM_PROMPT = SystemMessage(
    content=(PROMPT2)
)

# def duration_split(state: AgentState):
#     response = llm.invoke([
#         SYSTEM_PROMPT,
#         HumanMessage(content=state["text"]),
#     ])

#     state["split_result"] = response.content
#     return state

def duration_split(state: VCAgentState):
    
    for i,tutorial in enumerate(state['tech_updates']):
        print (f"Splitting tutorials into smaller fragments: {i+1}/{len(state['tech_updates'])}")
        task = f"Split the given tutorial with total duration of {state['structured_legacy'][i]['duation']} into fragments of 3-4 minutes tutorials delivering subtopics: {tutorial['updated_subtopics']}."
        result = llm.invoke([SYSTEM_PROMPT,HumanMessage(content=task),])
        # response = llm.invoke([
        # SYSTEM_PROMPT,
        # HumanMessage(content=state["text"]),
    # ])
        
        # raw_content = (search_result['messages'][-1].content[-1]['text'])     # use when using gemini
        # raw_content = (result['messages'][-1].content)                   # use when using openRouter
        raw_content = result.content
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            
        parsed = json.loads(raw_content)
        
        tutorial['updated_subtopics'] = parsed
        
    return state
    
    
from src.utils.VC_utils import llm, SEMAPHORE_CONFIG
from langchain.schema import SystemMessage
from src.core.state import VCAgentState
import json

from langchain.schema import SystemMessage, HumanMessage
import asyncio
from typing import Dict

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

async def _split_single_tutorial(semaphore: asyncio.Semaphore, index: int, total: int, tutorial: Dict, legacy_duration: str) -> Dict:
    """Split a single tutorial with semaphore control."""
    async with semaphore:
        print(f"Splitting tutorials into smaller fragments: {index+1}/{total}")
        task = f"Split the given tutorial with total duration of {legacy_duration} into fragments of 3-4 minutes tutorials delivering subtopics: {tutorial['updated_subtopics']}."
        
        # Run LLM invoke in executor since it's synchronous
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: llm.invoke([SYSTEM_PROMPT, HumanMessage(content=task)]))
        
        raw_content = result.content
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        
        parsed = json.loads(raw_content)
        return (index, parsed)


async def duration_split_async(state: VCAgentState, semaphore_limit: int = None) -> VCAgentState:
    """Split tutorials concurrently with semaphore limit."""
    if semaphore_limit is None:
        semaphore_limit = SEMAPHORE_CONFIG["split"]
    
    tech_updates = state['tech_updates']
    structured_legacy = state['structured_legacy']
    print(f"Splitting {len(tech_updates)} tutorials with semaphore limit: {semaphore_limit}")
    
    semaphore = asyncio.Semaphore(semaphore_limit)
    tasks = [
        _split_single_tutorial(semaphore, i, len(tech_updates), tutorial, structured_legacy[i]['duation'])
        for i, tutorial in enumerate(tech_updates)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            print(f"Error during split: {result}")
        else:
            index, parsed = result
            state['tech_updates'][index]['updated_subtopics'] = parsed
    
    return state


def duration_split(state: VCAgentState) -> VCAgentState:
    """Synchronous wrapper for duration_split_async."""
    return asyncio.run(duration_split_async(state))
    
    
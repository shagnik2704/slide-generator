from src.core.state import VCAgentState
from src.utils.VC_utils import llm, search_tool, SEMAPHORE_CONFIG
import json
from langchain.schema import SystemMessage, HumanMessage
import asyncio
from typing import Dict, List

SYSTEM_PROMPT = SystemMessage(
    content=(
        '''
        You are a tech intelligence agent that provides the latest updates on version changes and modificaions on topics based on user queries.
        Use the response provided by search tool to find relevant and recent information.
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
        '''   
    )
)

# def tech_intelligence_agent(state: VCAgentState):
#     query = f"""
#     Find latest stable version of {state['title']} and version updates corresponding to the subtopics: {state['subtopics']}.
#     """
    
#     response = llm_openRouter.invoke([
#         SYSTEM_PROMPT,
#         HumanMessage(content=query),
#     ])

#     state["tech_updates"] = response.content
#     return state



# agent = create_agent(llm_openRouter,
#                      tools=[search_tool],
#                      system_prompt='''
#                      You are a tech intelligence agent that provides the latest updates on version changes and modificaions on topics based on user queries.
#                      Use the search tool to find relevant and recent information.
#                      You are given tutorial title and subtopics. Return latest stable version name in updated title and version updates corresponding to the subtopics in updated subtopics.
#                      Maintain a log by clearly highlighting what changes are made from older version to newer version. Make an entry only when there is some change.
#                      If you cannot find newer updates, tag the older subtopics as 'deprecated' in the log, and if possible find an alternative and present it in one line.
#                      Return the output in the JSON format:
#                         {
#                             "updated_title": "<updated title or same title if no change>" <return type: str>,
#                             "updated_subtopics": "<updated subtopics with desired version changes>" <return type: str>
#                             "logs": "<List of updates numbered sequentially>" <return type: List>
#                         }
#                     Follow the format strictly.
#                     Return only the resultant JSON and nothing else.
#                     ''')
def chunk_text(text, max_len=250):
    chunks, current = [], ""
    for item in text.split(","):
        if len(current) + len(item) < max_len:
            current += item + ","
        else:
            chunks.append(current.strip(","))
            current = item + ","
    chunks.append(current.strip(","))
    return chunks

async def _update_single_tutorial(semaphore: asyncio.Semaphore, index: int, total: int, tutorial: Dict) -> Dict:
    """Update a single tutorial with semaphore control."""
    async with semaphore:
        print(f"Updating tutorials and its contents to latest version: {index+1}/{total}")
        chunks = chunk_text(tutorial['subtopics'])

        # Parallelize search operations within this tutorial
        async def search_chunk(chunk):
            query = f"""
            Find latest stable version of {tutorial['title']} and version updates corresponding to the subtopics: {chunk}.
            """
            # Run search_tool in executor since it's synchronous
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, search_tool, query)
        
        # Execute all chunk searches concurrently
        search_results = await asyncio.gather(*[search_chunk(chunk) for chunk in chunks])
        
        task = f'''
        Here are the search results from the search tool:{search_results}.
        Update the tutorial title and the subtopics taking resferrnce to the search results.
        Maintain logs and return JSON in required format.
        '''
        
        # Run LLM invoke in executor since it's synchronous
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: llm.invoke([
            SYSTEM_PROMPT,
            HumanMessage(content=task),
        ]))
        
        raw_content = result.content
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        
        parsed = json.loads(raw_content)
        return parsed


async def tech_intelligence_agent_async(state: VCAgentState, semaphore_limit: int = None) -> VCAgentState:
    """Update tutorials concurrently with semaphore limit."""
    if semaphore_limit is None:
        semaphore_limit = SEMAPHORE_CONFIG["update"]
    
    tutorials = state['structured_legacy']
    print(f"Updating {len(tutorials)} tutorials with semaphore limit: {semaphore_limit}")
    
    semaphore = asyncio.Semaphore(semaphore_limit)
    tasks = [
        _update_single_tutorial(semaphore, i, len(tutorials), tutorial)
        for i, tutorial in enumerate(tutorials)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            print(f"Error during update: {result}")
        else:
            state['tech_updates'].append(result)
    
    return state


def tech_intelligence_agent(state: VCAgentState) -> VCAgentState:
    """Synchronous wrapper for tech_intelligence_agent_async."""
    return asyncio.run(tech_intelligence_agent_async(state))
    # return state['tech_updates']
    
    # return search_result
    

# state = {'legacy_raw_data': 'https://spoken-tutorial.org/watch/Linux+AWK/Overview+of+Linux+AWK/English/', 'structured_legacy': [{'title': 'Overview of Linux AWK', 'subtopics': 'About awk commands, AWK Process, Glimpse of Spoken Tutorials available on AWK', 'duation': '00:08:20'}, {'title': 'Basics of awk', 'subtopics': 'Awk Preliminaries, Selection criteria, action, Formatted printing - printf, Fields and -F option, Regular expressions, NR - number of records, Variables', 'duation': '00:08:19'}], 'tech_updates': [], 'final_table': {}, 'errors': []}
# state = DSpace_state
# result = tech_intelligence_agent(state)

# print (result)

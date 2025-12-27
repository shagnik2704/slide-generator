"""LLM utility functions for outline chat."""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def generate_llm_text(
    prompt: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    system_prompt: str = "You are a helpful assistant used inside a Spoken Tutorial course outline creation system.",
) -> str:
    """
    Generate text using OpenAI chat completions.

    This route must use ONLY OpenAI (no Gemini / Google GenAI).
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


def friendly_rewrite_question(base_question: str, outline_type: str, phase: str) -> str:
    """
    Use OpenAI to lightly rewrite a base question in a more friendly,
    conversational tone while keeping the meaning the same.
    Falls back to the original question on any error.
    Ensures the final question is under 100 characters.
    """
    try:
        prompt = f"""You are a warm, supportive assistant helping to interview a subject-matter expert for a Spoken Tutorial course outline.

Rewrite the following question in a more friendly, conversational way, but keep the meaning and structure the same.

Guidelines:
- Address the user as "you".
- Sound encouraging and collaborative (as if you are gently guiding them).
- Keep it within 1–2 sentences.
- Do NOT add extra instructions, tips, examples, or emojis beyond what is already present.
- Do NOT change any technical terms or placeholders.
- CRITICAL: The final question MUST be under 100 characters. If needed, shorten it while keeping essential information.

Question:
{base_question}

Return ONLY the rewritten question text (under 100 characters)."""

        rewritten = generate_llm_text(
            prompt,
            temperature=0.4,
            max_tokens=128,  # Reduced to encourage shorter output
            system_prompt="You are a warm but precise rewriting assistant. Always keep questions under 100 characters.",
        )
        if len(rewritten.strip()) < 5:
            return base_question
        
        rewritten = rewritten.strip()
        
        # Enforce 100 character limit - truncate if needed
        if len(rewritten) > 100:
            # Try to truncate at a sentence boundary or word boundary
            truncated = rewritten[:97] + "..."
            # If the original base question is shorter, use it instead
            if len(base_question) <= 100:
                return base_question
            return truncated
        
        return rewritten
    except Exception:
        # Fallback: if base question is already under 100 chars, return it
        if len(base_question) <= 100:
            return base_question
        # Otherwise truncate base question
        return base_question[:97] + "..."


def get_example_answer_hint(
    outline_type: str,
    phase: str,
    base_question: str,
) -> str | None:
    """
    Use the LLM to generate a short, concrete example answer for the given question.

    The example is conditioned on:
    - the outline type (FOSS / ICT),
    - the current phase (warmup / outcomes / examples / structure / metadata),
    - and the exact question text.
    """
    outline_type = outline_type.upper()

    try:
        prompt = f"""You are helping a subject-matter expert fill a Spoken Tutorial course outline via chat.

Your task: given ONE question we are asking the user, write ONE SHORT, CONCRETE example answer that fits that question.

Guidelines:
- Answer as if you are the SME giving a good, realistic response.
- Keep it to a single line or a very short paragraph.
- Do NOT include explanations, meta-commentary, or phrases like "for example" or "you could say".
- Do NOT repeat the question text.
- Only return the example answer text itself.
- If the question is asking for a course name, outline name, tutorial title, or similar short title, make sure your answer is under 50 characters and uses only letters, numbers, and spaces (no special characters).

Context:
- Outline type: {outline_type}
- Phase: {phase}
- Question: {base_question}

Now return just ONE example answer that would be appropriate for this question."""

        example = generate_llm_text(
            prompt,
            temperature=0.4,
            max_tokens=128,
            system_prompt="You generate only short, concrete example answers for course-outline questions.",
        ).strip()

        # Basic sanity check – avoid empty or obviously long essays
        if not example or len(example) < 5 or len(example) > 400:
            return None

        return example
    except Exception:
        return None


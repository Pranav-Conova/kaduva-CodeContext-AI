"""LLM service supporting Google Gemini, xAI Grok, and Kimi (Moonshot via NVIDIA NIM)."""

import logging
import time
from openai import OpenAI
import google.generativeai as genai

from app.config import settings

logger = logging.getLogger("codecontext.llm")

_gemini_configured = False
_grok_client = None
_kimi_client = None


# ── Provider setup ──────────────────────────────────────────

def _ensure_gemini():
    """Configure the Gemini API key (once)."""
    global _gemini_configured
    if not _gemini_configured:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set. Please add it to your .env file.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_configured = True
        logger.info("Gemini configured (model: %s)", settings.LLM_MODEL)


def _get_grok_client() -> OpenAI:
    """Get or create the Grok (xAI) OpenAI-compatible client."""
    global _grok_client
    if _grok_client is None:
        if not settings.GROK_API_KEY:
            raise RuntimeError("GROK_API_KEY is not set. Please add it to your .env file.")
        _grok_client = OpenAI(
            api_key=settings.GROK_API_KEY,
            base_url="https://api.x.ai/v1",
        )
        logger.info("Grok configured (model: %s)", settings.GROK_MODEL)
    return _grok_client


def _get_kimi_client() -> OpenAI:
    """Get or create the Kimi (Moonshot via NVIDIA NIM) OpenAI-compatible client."""
    global _kimi_client
    if _kimi_client is None:
        if not settings.KIMI_API_KEY:
            raise RuntimeError("KIMI_API_KEY is not set. Please add it to your .env file.")
        _kimi_client = OpenAI(
            api_key=settings.KIMI_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1",
        )
        logger.info("Kimi configured (model: %s)", settings.KIMI_MODEL)
    return _kimi_client


# ── Prompt builders ─────────────────────────────────────────

def _qa_prompt(context: str, question: str) -> str:
    return f"""You are an expert code analyst. You are analyzing a software project.
You have access to the following relevant code from the repository:

{context}

---

User Question:
{question}

---

Instructions:
- Answer the question based on the code above.
- Reference specific files and functions when relevant.
- If the code doesn't contain enough information to fully answer, say so.
- Use markdown formatting for clarity.
- Be concise but thorough.
"""


def _edit_prompt(context: str, file_content: str, file_path: str, instruction: str) -> str:
    return f"""You are an expert software engineer. You need to modify a source file.

Here is relevant context from the project:

{context}

---

File to modify: {file_path}

```
{file_content}
```

---

Modification instruction:
{instruction}

---

IMPORTANT RULES:
1. Return the COMPLETE modified file content.
2. Do NOT omit any existing code unless the instruction specifically asks to remove it.
3. Do NOT add explanatory comments unless asked.
4. Return ONLY the code, no markdown code fences, no explanations before or after.
5. Preserve the original formatting style, indentation, and conventions.
"""


# ── Gemini calls ────────────────────────────────────────────

def _gemini_generate(prompt: str, temperature: float, max_tokens: int) -> str:
    _ensure_gemini()
    model = genai.GenerativeModel(settings.LLM_MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )
    return response.text


# ── Grok calls ──────────────────────────────────────────────

def _grok_generate(prompt: str, temperature: float, max_tokens: int) -> str:
    client = _get_grok_client()
    response = client.chat.completions.create(
        model=settings.GROK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


# ── Kimi calls ──────────────────────────────────────────────

def _kimi_generate(prompt: str, temperature: float, max_tokens: int) -> str:
    client = _get_kimi_client()
    response = client.chat.completions.create(
        model=settings.KIMI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


# ── Public API ──────────────────────────────────────────────

def _generate(prompt: str, temperature: float, max_tokens: int, provider: str = "gemini") -> str:
    """Route to the correct provider."""
    logger.info("LLM call via %s (%d chars, temp=%.1f)", provider, len(prompt), temperature)
    t0 = time.time()

    if provider == "grok":
        result = _grok_generate(prompt, temperature, max_tokens)
    elif provider == "kimi":
        result = _kimi_generate(prompt, temperature, max_tokens)
    else:
        result = _gemini_generate(prompt, temperature, max_tokens)

    logger.info("LLM responded in %.1fs (%d chars) [%s]", time.time() - t0, len(result), provider)
    return result


def ask_question(context: str, question: str, provider: str = "gemini") -> str:
    """
    Ask the LLM a question with code context.

    Args:
        context: Structured code context from retrieval.
        question: The user's question.
        provider: 'gemini', 'grok', or 'kimi'.

    Returns:
        The LLM's answer as a string.
    """
    prompt = _qa_prompt(context, question)
    return _generate(prompt, settings.LLM_CHAT_TEMPERATURE, 4096, provider)


def generate_code_edit(
    context: str, file_content: str, file_path: str, instruction: str,
    provider: str = "gemini",
) -> str:
    """
    Ask the LLM to modify a file based on an instruction.

    Args:
        context: Relevant code context from the project.
        file_content: The full content of the file to modify.
        file_path: Path of the file being edited.
        instruction: What modification to make.
        provider: 'gemini', 'grok', or 'kimi'.

    Returns:
        The complete modified file content.
    """
    prompt = _edit_prompt(context, file_content, file_path, instruction)
    result = _generate(prompt, settings.LLM_CODE_TEMPERATURE, 8192, provider)

    # Strip markdown code fences if present
    result = result.strip()
    if result.startswith("```"):
        lines = result.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        result = "\n".join(lines)

    return result

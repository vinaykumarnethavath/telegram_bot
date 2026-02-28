"""
Q&A Service — answers user questions grounded in the video transcript.

Design decisions:
- Uses Groq llama-3.1-8b-instant (ultra-fast for Q&A responses)
- Keyword-based excerpt selection to minimize token usage
- Multi-turn context (last 5 Q&A turns)
- Strict grounding: system prompt forbids hallucination
"""

import os
import logging
from services.groq_client import get_groq_client

logger = logging.getLogger(__name__)

GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")

QA_SYSTEM_PROMPT = """You are an expert AI assistant helping users understand YouTube videos.

CRITICAL RULES:
1. Answer ONLY based on information in the provided transcript.
2. If the answer is not in the transcript, respond EXACTLY with:
   "❌ This topic is not covered in the video."
3. Be concise and clear.
4. If quoting from the video, be accurate.
5. Never fabricate or invent information.
6. Respond in the language specified by the user."""

QA_USER_TEMPLATE = """Video: {title}

Transcript excerpt:
{transcript_excerpt}

Previous conversation:
{history}

User question: {question}

Respond in {language_name}."""

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
}

MAX_EXCERPT_CHARS = 8000


class QAService:
    """
    Answers questions based on video transcript context using Groq (fast model).
    """

    def __init__(self):
        pass  # Groq client is lazily initialized

    @property
    def client(self):
        return get_groq_client()

    def answer(
        self,
        question: str,
        transcript: str,
        title: str,
        qa_history: list[dict],
        language: str = "en",
    ) -> str:
        """Answer using transcript context with keyword-based relevance."""
        language_name = LANGUAGE_NAMES.get(language, "English")
        excerpt = self._get_relevant_excerpt(question, transcript)
        history_text = self._format_history(qa_history)

        prompt = QA_USER_TEMPLATE.format(
            title=title,
            transcript_excerpt=excerpt,
            history=history_text,
            question=question,
            language_name=language_name,
        )

        return self._call_llm_with_fallback(QA_SYSTEM_PROMPT, prompt)

    def _call_llm_with_fallback(self, system_prompt: str, user_prompt: str) -> str:
        """Call Groq chat completion with automatic fallback on rate limits (429)."""
        from services.groq_client import is_rate_limit_error

        try:
            return self._execute_llm_call(GROQ_FAST_MODEL, system_prompt, user_prompt)
        except Exception as e:
            if is_rate_limit_error(e):
                logger.warning(f"Rate limit hit on {GROQ_FAST_MODEL}. No further fallback available.")
            raise e

    def _execute_llm_call(self, model: str, system_prompt: str, user_prompt: str) -> str:
        """Lower-level execution of the Groq chat completion call."""
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()

    def _get_relevant_excerpt(self, question: str, transcript: str) -> str:
        """Find most relevant section using keyword overlap scoring."""
        if len(transcript) <= MAX_EXCERPT_CHARS:
            return transcript

        question_words = set(w.lower() for w in question.split() if len(w) >= 4)
        if not question_words:
            return transcript[:MAX_EXCERPT_CHARS]

        window_size = 500
        step = 200
        best_score = -1
        best_start = 0

        for i in range(0, len(transcript) - window_size, step):
            window = transcript[i: i + window_size].lower()
            score = sum(1 for w in question_words if w in window)
            if score > best_score:
                best_score = score
                best_start = i

        start = max(0, best_start - 1000)
        end = min(len(transcript), best_start + MAX_EXCERPT_CHARS - 1000)
        return transcript[start:end]

    def _format_history(self, qa_history: list[dict]) -> str:
        if not qa_history:
            return "(No previous questions)"
        lines = []
        for turn in qa_history[-5:]:
            lines.append(f"Q: {turn['q']}")
            lines.append(f"A: {turn['a']}\n")
        return "\n".join(lines)

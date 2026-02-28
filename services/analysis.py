"""
Analysis Service — provides in-depth analysis and action points from video transcripts.
Includes automatic fallback for Groq rate limits.
"""

import os
import logging
from services.groq_client import get_groq_client, is_rate_limit_error

logger = logging.getLogger(__name__)

GROQ_QUALITY_MODEL = os.getenv("GROQ_QUALITY_MODEL", "llama-3.3-70b-versatile")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")

DEEPDIVE_PROMPT = """Provide a comprehensive, in-depth analysis of this YouTube video.

Video Title: {title}
Transcript excerpt: {transcript_excerpt}

Respond in {language_name}. Structure your response as:

🔬 *Deep Dive Analysis: {title}*

📚 *Background & Context*:

🔑 *Core Arguments* (with evidence):
1.
2.
3.

💡 *Insights & Implications*:

🤔 *Critical Questions Raised*:

⭐ *Most Memorable Quote or Moment*:"""

ACTIONPOINTS_PROMPT = """Extract actionable advice, tips, and steps from this YouTube video.

Video Title: {title}
Transcript: {transcript_excerpt}

Respond in {language_name}:

✅ *Action Points: {title}*

🎯 *Immediate Actions* (do today):
•

📅 *Short-term Actions* (this week):
•

🚀 *Long-term Strategies*:
•

🛠️ *Tools/Resources Mentioned*:
•

⚡ *Quick Wins*:
•"""

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
}


class AnalysisService:
    def __init__(self):
        pass

    @property
    def client(self):
        return get_groq_client()

    def deep_dive(self, title: str, transcript: str, language: str = "en") -> str:
        language_name = LANGUAGE_NAMES.get(language, "English")
        prompt = DEEPDIVE_PROMPT.format(
            title=title,
            transcript_excerpt=transcript[:15000],  # Use more for deep dive
            language_name=language_name
        )
        return self._call_llm_with_fallback(prompt)

    def action_points(self, title: str, transcript: str, language: str = "en") -> str:
        language_name = LANGUAGE_NAMES.get(language, "English")
        prompt = ACTIONPOINTS_PROMPT.format(
            title=title,
            transcript_excerpt=transcript[:12000],
            language_name=language_name
        )
        return self._call_llm_with_fallback(prompt)

    def _call_llm_with_fallback(self, user_prompt: str) -> str:
        try:
            return self._execute_llm_call(GROQ_QUALITY_MODEL, user_prompt)
        except Exception as e:
            if is_rate_limit_error(e):
                logger.warning(f"Rate limit hit on {GROQ_QUALITY_MODEL}. Falling back to {GROQ_FAST_MODEL}.")
                return self._execute_llm_call(GROQ_FAST_MODEL, user_prompt)
            raise e

    def _execute_llm_call(self, model: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful AI research assistant."},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()

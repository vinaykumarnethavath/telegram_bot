"""
Key Terms Service — extracts a glossary of key terms/concepts from transcripts.

New feature for improved video understanding: surfaces vocabulary,
technical terms, and named entities mentioned in the video.
"""

import os
import logging
from services.groq_client import get_groq_client

logger = logging.getLogger(__name__)

GROQ_QUALITY_MODEL = os.getenv("GROQ_QUALITY_MODEL", "llama-3.3-70b-versatile")

KEYTERMS_PROMPT = """Extract the most important key terms, concepts, and named entities from this YouTube video transcript.

Video Title: {title}
Transcript:
{transcript}

Respond ONLY in {language_name}. Format exactly as:

🔑 *Key Terms & Concepts: {title}*

📚 *Technical/Domain Terms*:
• **Term**: Brief definition or context from the video

👤 *People & Organizations Mentioned*:
• **Name**: Role or context

💡 *Core Concepts Explained*:
• **Concept**: How it was explained in the video

🌐 *Tools, Products & Resources*:
• **Name**: Purpose or context mentioned

If a category is empty, write "None mentioned."
Keep definitions concise (1 line each)."""


class KeyTermsService:
    """Extracts key terms and a glossary from video transcripts."""

    def __init__(self):
        pass

    @property
    def client(self):
        return get_groq_client()

    def extract(self, title: str, transcript: str, language: str = "en") -> str:
        """Extract key terms from transcript and return formatted string."""
        from services.language import LANGUAGE_DISPLAY_NAMES
        language_name = LANGUAGE_DISPLAY_NAMES.get(language, "English")

        # For long transcripts, use first + last sections (intro + conclusion have most terms)
        if len(transcript) > 10000:
            excerpt = transcript[:5000] + "\n...\n" + transcript[-3000:]
        else:
            excerpt = transcript

        prompt = KEYTERMS_PROMPT.format(
            title=title,
            transcript=excerpt,
            language_name=language_name,
        )

        response = self.client.chat.completions.create(
            model=GROQ_QUALITY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1200,
        )
        return response.choices[0].message.content.strip()

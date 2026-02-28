"""
Sentiment & Tone Analysis Service — analyses the overall tone of the video.

New feature: gives users a quick emotional/tone read before deciding to watch.
Uses Groq fast model for low latency.
"""

import os
from services.groq_client import get_groq_client

GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")

SENTIMENT_PROMPT = """Analyse the overall tone and sentiment of this YouTube video based on its transcript.

Video Title: {title}
Transcript excerpt:
{excerpt}

Respond in {language_name}. Format exactly as:

🎭 *Video Tone Analysis: {title}*

📊 *Overall Sentiment*: [Positive / Neutral / Negative / Mixed] (with brief reason)

🎙️ *Speaker Tone*: [e.g., Enthusiastic, Calm, Persuasive, Educational, Critical, Inspirational]

😊 *Emotional Moments*:
• [Timestamp if available] — [emotion and trigger]

⚡ *Energy Level*: [High / Medium / Low] — [brief explanation]

🎯 *Best Suited For*: [type of viewer who'd enjoy this most]"""


class SentimentService:
    """Analyses the emotional tone and sentiment of a video transcript."""

    def __init__(self):
        pass

    @property
    def client(self):
        return get_groq_client()

    def analyse(self, title: str, transcript: str, language: str = "en") -> str:
        from services.language import LANGUAGE_DISPLAY_NAMES
        language_name = LANGUAGE_DISPLAY_NAMES.get(language, "English")

        excerpt = transcript[:6000] if len(transcript) > 6000 else transcript

        prompt = SENTIMENT_PROMPT.format(
            title=title,
            excerpt=excerpt,
            language_name=language_name,
        )

        response = self.client.chat.completions.create(
            model=GROQ_FAST_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=700,
        )
        return response.choices[0].message.content.strip()

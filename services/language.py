"""
Language Service — language detection and multi-language response support.
Uses Groq (llama-3.1-8b-instant) for fast translation.
"""

import re
import os
import logging
from services.groq_client import get_groq_client

logger = logging.getLogger(__name__)

GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")

SUPPORTED_LANGUAGES: dict[str, str] = {
    "english": "en",
    "hindi": "hi",
    "kannada": "kn",
    "tamil": "ta",
    "telugu": "te",
    "marathi": "mr",
    # Native-script variants
    "हिंदी": "hi",
    "ಕನ್ನಡ": "kn",
    "தமிழ்": "ta",
    "తెలుగు": "te",
    "मराठी": "mr",
}

LANGUAGE_DISPLAY_NAMES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi (हिंदी)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "mr": "Marathi (मराठी)",
}

LANGUAGE_REQUEST_PATTERNS = [
    r"\b(?:in|using|switch\s+to|respond\s+in|reply\s+in|speak\s+in|translate\s+(?:to|in)|summarize\s+in|explain\s+in)\s+(\w+)\b",
    r"\b(\w+)\s+(?:me\s+)?(?:mein|me)\b",
]


class LanguageService:
    def __init__(self):
        pass  # Groq client is lazily initialized

    @property
    def client(self):
        return get_groq_client()

    def detect_language_request(self, text: str) -> str | None:
        text_lower = text.lower().strip()

        direct = re.match(r"(?:language[:\s]+|/language\s+)(\w+)", text_lower)
        if direct:
            return SUPPORTED_LANGUAGES.get(direct.group(1).lower())

        for pattern in LANGUAGE_REQUEST_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                code = SUPPORTED_LANGUAGES.get(match.group(1).lower())
                if code:
                    return code

        for lang_word, code in SUPPORTED_LANGUAGES.items():
            if lang_word.lower() in text_lower:
                return code

        return None

    def get_display_name(self, lang_code: str) -> str:
        return LANGUAGE_DISPLAY_NAMES.get(lang_code, "English")

    def is_supported(self, lang_code: str) -> bool:
        return lang_code in LANGUAGE_DISPLAY_NAMES

    def translate_text(self, text: str, target_lang: str) -> str:
        """Translate text using Groq fast model."""
        if target_lang == "en":
            return text

        target_name = LANGUAGE_DISPLAY_NAMES.get(target_lang, target_lang)
        response = self.client.chat.completions.create(
            model=GROQ_FAST_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a professional translator. Translate the following text "
                        f"to {target_name}. Keep all emojis, formatting, and structure intact. "
                        f"Only translate the human-readable text."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        return response.choices[0].message.content.strip()

    def list_supported_languages(self) -> str:
        lines = ["🌐 *Supported Languages:*"]
        for code, display in LANGUAGE_DISPLAY_NAMES.items():
            flag = "🇬🇧" if code == "en" else "🇮🇳"
            lines.append(f"{flag} {display} — type: `{code.upper()}`")
        lines.append("\nExample: `Summarize in Hindi` or `/language kannada`")
        return "\n".join(lines)

"""
Groq client factory — lazy initialization to avoid GroqError during import
when GROQ_API_KEY is not set (e.g., during unit testing with mocks).
"""

import os
from groq import Groq

_client = None


def get_groq_client() -> Groq:
    """Return a singleton Groq client, created lazily on first call."""
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def create_groq_client() -> Groq:
    """Create a new Groq client (used in tests / cases requiring fresh client)."""
    return Groq(api_key=os.getenv("GROQ_API_KEY", "test-key"))


def is_rate_limit_error(e: Exception) -> bool:
    """Check if an exception is a Groq RateLimitError (429)."""
    from groq import RateLimitError
    return isinstance(e, RateLimitError)

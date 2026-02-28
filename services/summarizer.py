"""
Summarizer Service — generates structured summaries using Groq LLaMA.

Design decisions:
- Uses Groq (llama-3.3-70b-versatile) for quality summaries
- Uses map-reduce for long transcripts
- Structured output enforced via prompt (key points, timestamps, takeaway)
- Language-aware responses
"""

import os
import logging
from dataclasses import dataclass
from services.groq_client import get_groq_client

logger = logging.getLogger(__name__)

GROQ_QUALITY_MODEL = os.getenv("GROQ_QUALITY_MODEL", "llama-3.3-70b-versatile")
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")

SUMMARY_SYSTEM_PROMPT = """You are an expert AI research assistant specializing in summarizing YouTube videos.
Your job is to analyze a video transcript and produce a clear, structured summary.

IMPORTANT RULES:
- Extract ONLY information present in the transcript
- Be concise but comprehensive
- Format exactly as specified
- For timestamps, use MM:SS format from the transcript cues"""

SUMMARY_USER_TEMPLATE = """Analyze this YouTube video transcript and produce a structured summary.

Video Title: {title}
Transcript:
{transcript}

MANDATORY INSTRUCTION: Respond ONLY in {language_name}.
You MUST translate EVERYTHING into {language_name}, including the labels and headers below. 
Do NOT keep ANY English headers like "Video Title", "Key Points", "Timestamps", or "Core Takeaway".

Use this EXACT structure, but translate the labels into {language_name}:

🎥 *Video Title*: {title}

📌 *5 Key Points*:
1.
2.
3.
4.
5.

⏱ *Important Timestamps*:
- [MM:SS] — Topic/moment

🧠 *Core Takeaway*:
One powerful sentence summarizing the main insight of this video."""

PARTIAL_SUMMARY_PROMPT = """Summarize the following transcript segment in 3-5 bullet points.
Focus on key facts, arguments, and insights. Be concise.

Transcript segment:
{chunk}

Respond with a bullet-point list only."""

FINAL_MERGE_TEMPLATE = """You are synthesizing partial summaries of a long YouTube video into one final structured summary.

Video Title: {title}
Partial summaries from transcript segments:
{partial_summaries}

MANDATORY INSTRUCTION: Respond ONLY in {language_name}.
You MUST translate EVERYTHING into {language_name}, including the labels and headers below. 
Do NOT keep ANY English headers like "Video Title", "Key Points", "Timestamps", or "Core Takeaway".

Use this EXACT structure, but translate the labels into {language_name}:

🎥 *Video Title*: {title}

📌 *5 Key Points*:
1.
2.
3.
4.
5.

⏱ *Important Timestamps*:
- [MM:SS] — Topic/moment (use any timestamps mentioned in the partial summaries)

🧠 *Core Takeaway*:
One powerful sentence summarizing the main insight of this video."""

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi (हिंदी)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "mr": "Marathi (मराठी)",
}


@dataclass
class Summary:
    text: str
    language: str
    video_id: str
    video_title: str


class SummarizerService:
    """
    Generates structured summaries from video transcripts using Groq LLaMA.
    """

    def __init__(self):
        pass  # Groq client is lazily initialized

    @property
    def client(self):
        return get_groq_client()

    def summarize(
        self, video_id: str, title: str, chunks: list[str], language: str = "en"
    ) -> Summary:
        """Generate a structured summary with map-reduce for long transcripts."""
        language_name = LANGUAGE_NAMES.get(language, "English")

        if len(chunks) == 1:
            text = self._summarize_single(chunks[0], title, language_name)
        else:
            text = self._summarize_map_reduce(chunks, title, language_name)

        return Summary(
            text=text,
            language=language,
            video_id=video_id,
            video_title=title,
        )

    def _summarize_single(self, transcript: str, title: str, language_name: str) -> str:
        prompt = SUMMARY_USER_TEMPLATE.format(
            title=title,
            transcript=transcript,
            language_name=language_name,
        )
        return self._call_llm_with_fallback(SUMMARY_SYSTEM_PROMPT, prompt)

    def _summarize_map_reduce(self, chunks: list[str], title: str, language_name: str) -> str:
        logger.info(f"Map-reduce summarization for {len(chunks)} chunks")
        partial_summaries = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Summarizing chunk {i + 1}/{len(chunks)}")
            partial = self._call_llm_with_fallback(
                "You are an expert summarizer.",
                PARTIAL_SUMMARY_PROMPT.format(chunk=chunk),
            )
            partial_summaries.append(f"[Segment {i + 1}]\n{partial}")

        merged = "\n\n".join(partial_summaries)
        prompt = FINAL_MERGE_TEMPLATE.format(
            title=title,
            partial_summaries=merged,
            language_name=language_name,
        )
        return self._call_llm_with_fallback(SUMMARY_SYSTEM_PROMPT, prompt)

    def _call_llm_with_fallback(self, system_prompt: str, user_prompt: str) -> str:
        """Call Groq chat completion with automatic fallback on rate limits (429)."""
        from services.groq_client import is_rate_limit_error

        try:
            # Try high-quality model first
            return self._execute_llm_call(GROQ_QUALITY_MODEL, system_prompt, user_prompt)
        except Exception as e:
            if is_rate_limit_error(e):
                logger.warning(
                    f"Rate limit hit on {GROQ_QUALITY_MODEL}. Falling back to {GROQ_FAST_MODEL}."
                )
                return self._execute_llm_call(GROQ_FAST_MODEL, system_prompt, user_prompt)
            raise e

    def _execute_llm_call(self, model: str, system_prompt: str, user_prompt: str) -> str:
        """Lower-level execution of the Groq chat completion call."""
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()

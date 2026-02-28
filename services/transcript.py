"""
Transcript Service — fetches YouTube transcripts using youtube-transcript-api v1.x.

Design decisions:
- Uses youtube-transcript-api (no YouTube Data API key required)
- Prefers English transcripts, falls back to auto-generated ones
- Handles long transcripts by chunking for downstream LLM calls
- Validates YouTube URLs before attempting fetch
- Results are cached in SessionStore to avoid redundant API calls
"""

import re
import os
from dataclasses import dataclass
from typing import Optional

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
)

# Patterns to extract video ID from various YouTube URL formats
YT_URL_PATTERNS = [
    r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})",
]

MAX_TRANSCRIPT_CHARS = int(os.getenv("MAX_TRANSCRIPT_TOKENS", "12000")) * 4  # ~4 chars/token

# v1.x API instance
ytt_api = YouTubeTranscriptApi()


class TranscriptError(Exception):
    """Base error for transcript issues."""
    pass


class InvalidURLError(TranscriptError):
    pass


class TranscriptNotFoundError(TranscriptError):
    pass


class TranscriptDisabledError(TranscriptError):
    pass


@dataclass
class TranscriptResult:
    video_id: str
    title: str
    transcript: str           # Full formatted transcript text
    chunks: list[str]         # Transcript split into LLM-friendly chunks
    has_timestamps: bool
    language: str


class TranscriptService:
    """
    Fetches and processes YouTube video transcripts.
    """

    def extract_video_id(self, url: str) -> str:
        """Extract 11-char video ID from any YouTube URL format."""
        url = url.strip()
        for pattern in YT_URL_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise InvalidURLError(
            f"❌ Could not extract a video ID from the provided URL.\n"
            f"Please send a valid YouTube link, e.g.:\n"
            f"https://youtube.com/watch?v=dQw4w9WgXcQ"
        )

    def fetch(self, url: str) -> TranscriptResult:
        """
        Fetch transcript for a YouTube video URL.
        Returns a TranscriptResult with full text and chunks.
        Raises TranscriptError subclasses on failure.
        """
        video_id = self.extract_video_id(url)
        return self.fetch_by_id(video_id)

    def fetch_by_id(self, video_id: str) -> TranscriptResult:
        """Fetch transcript by video ID (v1.x API)."""
        try:
            # v1.x: list available transcripts
            transcript_list = ytt_api.list(video_id)
            transcript_obj = self._pick_best_transcript(transcript_list)
            fetched = transcript_obj.fetch()
            lang = transcript_obj.language_code

            # Convert FetchedTranscript snippets to list of dicts
            entries = [
                {"start": s.start, "duration": s.duration, "text": s.text}
                for s in fetched
            ]

        except NoTranscriptFound:
            raise TranscriptNotFoundError(
                "❌ No transcript found for this video.\n"
                "This video may not have captions or subtitles available."
            )
        except Exception as e:
            err_str = str(e).lower()
            if "disabled" in err_str or "transcriptsdisabled" in err_str:
                raise TranscriptDisabledError(
                    "❌ Transcripts are disabled for this video.\n"
                    "The creator has turned off subtitles/CC for this video."
                )
            if "unavailable" in err_str or "private" in err_str:
                raise TranscriptError(
                    "❌ This video is unavailable (private, deleted, or region-locked)."
                )
            raise TranscriptError(f"❌ Failed to fetch transcript: {str(e)}")

        # Format transcript with timestamps
        full_text_with_ts = self._format_with_timestamps(entries)
        plain_text = self._format_plain(entries)

        # Chunk for LLM calls
        chunks = self._chunk_text(plain_text)

        # Try to get title from metadata (best-effort, no API key needed)
        title = self._try_get_title(video_id)

        return TranscriptResult(
            video_id=video_id,
            title=title,
            transcript=plain_text,
            chunks=chunks,
            has_timestamps=True,
            language=lang,
        )

    def _pick_best_transcript(self, transcript_list):
        """Pick English first, then any manually created, then any auto-generated."""
        try:
            return transcript_list.find_transcript(["en", "en-US", "en-GB"])
        except NoTranscriptFound:
            pass
        # Try any manually created transcript
        for t in transcript_list:
            if not t.is_generated:
                return t
        # Fall back to first available (auto-generated)
        for t in transcript_list:
            return t
        raise NoTranscriptFound(None, None)

    def _format_with_timestamps(self, entries: list) -> str:
        """Format entries as '[MM:SS] text' lines."""
        lines = []
        for entry in entries:
            start = int(entry.get("start", 0))
            mins, secs = divmod(start, 60)
            text = entry.get("text", "").replace("\n", " ").strip()
            lines.append(f"[{mins:02d}:{secs:02d}] {text}")
        return "\n".join(lines)

    def _format_plain(self, entries: list) -> str:
        """Format entries as plain text (no timestamps), for Q&A context."""
        parts = []
        for entry in entries:
            text = entry.get("text", "").replace("\n", " ").strip()
            if text:
                parts.append(text)
        return " ".join(parts)

    def _chunk_text(self, text: str) -> list[str]:
        """
        Split text into chunks of ~MAX_TRANSCRIPT_CHARS characters.
        Splits on sentence boundaries where possible.
        """
        if len(text) <= MAX_TRANSCRIPT_CHARS:
            return [text]

        chunks = []
        while len(text) > MAX_TRANSCRIPT_CHARS:
            # Find nearest sentence break before limit
            cut = MAX_TRANSCRIPT_CHARS
            for delim in [". ", "? ", "! ", "\n"]:
                idx = text.rfind(delim, 0, MAX_TRANSCRIPT_CHARS)
                if idx > MAX_TRANSCRIPT_CHARS // 2:
                    cut = idx + len(delim)
                    break
            chunks.append(text[:cut].strip())
            text = text[cut:].strip()

        if text:
            chunks.append(text)

        return chunks

    def _try_get_title(self, video_id: str) -> str:
        """Try to get video title via oembed (no API key needed)."""
        try:
            import urllib.request
            import json
            url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read())
                return data.get("title", f"YouTube Video ({video_id})")
        except Exception:
            return f"YouTube Video ({video_id})"

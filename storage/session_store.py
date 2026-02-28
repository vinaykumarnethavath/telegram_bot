"""
Session Store — per-user session management with transcript caching.

Design:
- In-memory dict for fast access (no persistence overhead)
- Transcript cache shared across users by video_id (avoids re-fetching)
- Sessions expire after SESSION_TIMEOUT seconds of inactivity
"""

import os
import time
import threading
from dataclasses import dataclass, field
from typing import Optional

SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "7200"))  # 2 hours


@dataclass
class Session:
    user_id: int
    video_id: Optional[str] = None
    video_title: Optional[str] = None
    transcript: Optional[str] = None      # Full transcript text
    summary: Optional[str] = None         # Last generated summary
    language: str = "en"                  # Active response language
    qa_history: list = field(default_factory=list)  # [(question, answer), ...]
    last_active: float = field(default_factory=time.time)

    def touch(self):
        self.last_active = time.time()

    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > SESSION_TIMEOUT


class SessionStore:
    """
    Thread-safe in-memory session store with shared transcript cache.
    """

    def __init__(self):
        self._sessions: dict[int, Session] = {}
        self._transcript_cache: dict[str, dict] = {}  # video_id -> {title, transcript}
        self._lock = threading.Lock()
        self._stats: dict[str, int] = {"videos_processed": 0, "questions_answered": 0}
        self._start_cleanup_thread()

    # -------------------------
    # Session management
    # -------------------------

    def get_session(self, user_id: int) -> Session:
        """Get or create a session for the given user."""
        with self._lock:
            session = self._sessions.get(user_id)
            if session is None or session.is_expired():
                session = Session(user_id=user_id)
                self._sessions[user_id] = session
            session.touch()
            return session

    def save_session(self, session: Session):
        with self._lock:
            session.touch()
            self._sessions[session.user_id] = session

    def clear_session(self, user_id: int):
        with self._lock:
            self._sessions.pop(user_id, None)

    def set_language(self, user_id: int, language: str):
        session = self.get_session(user_id)
        session.language = language
        self.save_session(session)

    def get_language(self, user_id: int) -> str:
        return self.get_session(user_id).language

    def add_qa(self, user_id: int, question: str, answer: str):
        session = self.get_session(user_id)
        session.qa_history.append({"q": question, "a": answer})
        # Keep only the last 10 turns to control context size
        if len(session.qa_history) > 10:
            session.qa_history = session.qa_history[-10:]
        self.save_session(session)

    # -------------------------
    # Transcript cache
    # -------------------------

    def cache_transcript(self, video_id: str, title: str, transcript: str, chunks: list = None):
        with self._lock:
            self._transcript_cache[video_id] = {
                "title": title,
                "transcript": transcript,
                "chunks": chunks or [transcript],
                "cached_at": time.time(),
            }

    def get_cached_transcript(self, video_id: str) -> Optional[dict]:
        with self._lock:
            return self._transcript_cache.get(video_id)

    def is_transcript_cached(self, video_id: str) -> bool:
        return video_id in self._transcript_cache

    # -------------------------
    # Usage stats
    # -------------------------

    def increment_stat(self, key: str, amount: int = 1):
        with self._lock:
            self._stats[key] = self._stats.get(key, 0) + amount

    def get_stats(self) -> dict:
        with self._lock:
            return {
                **self._stats,
                "active_sessions": len(self._sessions),
                "cached_videos": len(self._transcript_cache),
            }

    # -------------------------
    # Internal cleanup
    # -------------------------

    def _cleanup_expired_sessions(self):
        while True:
            time.sleep(600)  # Check every 10 minutes
            with self._lock:
                expired = [uid for uid, s in self._sessions.items() if s.is_expired()]
                for uid in expired:
                    del self._sessions[uid]

    def _start_cleanup_thread(self):
        t = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        t.start()


# Global singleton
session_store = SessionStore()

"""
Tests for the SessionStore.
"""

import time
import unittest
from storage.session_store import SessionStore, Session


class TestSessionStore(unittest.TestCase):

    def setUp(self):
        self.store = SessionStore()

    def test_create_new_session(self):
        session = self.store.get_session(1001)
        self.assertIsInstance(session, Session)
        self.assertEqual(session.user_id, 1001)
        self.assertEqual(session.language, "en")

    def test_save_and_retrieve_session(self):
        session = self.store.get_session(1002)
        session.video_title = "Test Video"
        session.language = "hi"
        self.store.save_session(session)

        retrieved = self.store.get_session(1002)
        self.assertEqual(retrieved.video_title, "Test Video")
        self.assertEqual(retrieved.language, "hi")

    def test_clear_session(self):
        session = self.store.get_session(1003)
        session.transcript = "some transcript"
        self.store.save_session(session)
        self.store.clear_session(1003)

        fresh = self.store.get_session(1003)
        self.assertIsNone(fresh.transcript)

    def test_set_and_get_language(self):
        self.store.set_language(1004, "kn")
        self.assertEqual(self.store.get_language(1004), "kn")

    def test_add_qa_history(self):
        self.store.add_qa(1005, "What is the topic?", "Machine learning")
        session = self.store.get_session(1005)
        self.assertEqual(len(session.qa_history), 1)
        self.assertEqual(session.qa_history[0]["q"], "What is the topic?")
        self.assertEqual(session.qa_history[0]["a"], "Machine learning")

    def test_qa_history_limit(self):
        for i in range(15):
            self.store.add_qa(1006, f"Q{i}", f"A{i}")
        session = self.store.get_session(1006)
        self.assertLessEqual(len(session.qa_history), 10)

    def test_transcript_cache(self):
        self.store.cache_transcript(
            "abc123", "Test Video", "Full transcript text", chunks=["chunk1"]
        )
        self.assertTrue(self.store.is_transcript_cached("abc123"))
        cached = self.store.get_cached_transcript("abc123")
        self.assertEqual(cached["title"], "Test Video")
        self.assertEqual(cached["transcript"], "Full transcript text")
        self.assertEqual(cached["chunks"], ["chunk1"])

    def test_transcript_cache_miss(self):
        self.assertFalse(self.store.is_transcript_cached("not_exist"))
        self.assertIsNone(self.store.get_cached_transcript("not_exist"))

    def test_session_not_expired_fresh(self):
        session = self.store.get_session(1007)
        self.assertFalse(session.is_expired())

    def test_session_is_expired(self):
        session = Session(user_id=9999)
        session.last_active = time.time() - 10000  # Way in the past
        self.assertTrue(session.is_expired())


if __name__ == "__main__":
    unittest.main()

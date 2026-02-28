"""
Tests for TranscriptService.
"""

import unittest
from unittest.mock import patch, MagicMock
from services.transcript import (
    TranscriptService,
    InvalidURLError,
    TranscriptDisabledError,
    TranscriptNotFoundError,
)
from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound


class TestTranscriptService(unittest.TestCase):

    def setUp(self):
        self.service = TranscriptService()

    # --- URL extraction ---

    def test_extract_standard_url(self):
        vid_id = self.service.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(vid_id, "dQw4w9WgXcQ")

    def test_extract_short_url(self):
        vid_id = self.service.extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(vid_id, "dQw4w9WgXcQ")

    def test_extract_shorts_url(self):
        vid_id = self.service.extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ")
        self.assertEqual(vid_id, "dQw4w9WgXcQ")

    def test_extract_embed_url(self):
        vid_id = self.service.extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ")
        self.assertEqual(vid_id, "dQw4w9WgXcQ")

    def test_invalid_url_raises(self):
        with self.assertRaises(InvalidURLError):
            self.service.extract_video_id("https://google.com/search?q=test")

    def test_non_url_raises(self):
        with self.assertRaises(InvalidURLError):
            self.service.extract_video_id("just some random text")

    # --- Transcript fetching (mocked) ---

    @patch("services.transcript.ytt_api")
    def test_fetch_success(self, mock_ytt_api):
        # Mock snippet objects
        mock_snippet1 = MagicMock()
        mock_snippet1.start = 0.0
        mock_snippet1.duration = 5.0
        mock_snippet1.text = "Hello world"
        mock_snippet2 = MagicMock()
        mock_snippet2.start = 5.0
        mock_snippet2.duration = 5.0
        mock_snippet2.text = "This is a test"

        mock_transcript_obj = MagicMock()
        mock_transcript_obj.language_code = "en"
        mock_transcript_obj.is_generated = False
        mock_fetched = MagicMock()
        mock_fetched.__iter__ = MagicMock(return_value=iter([mock_snippet1, mock_snippet2]))
        mock_transcript_obj.fetch.return_value = mock_fetched

        mock_transcript_list = MagicMock()
        mock_transcript_list.find_transcript.return_value = mock_transcript_obj
        mock_ytt_api.list.return_value = mock_transcript_list

        result = self.service.fetch_by_id("dQw4w9WgXcQ")
        self.assertEqual(result.video_id, "dQw4w9WgXcQ")
        self.assertIn("Hello world", result.transcript)
        self.assertEqual(result.language, "en")
        self.assertIsInstance(result.chunks, list)
        self.assertGreater(len(result.chunks), 0)

    @patch("services.transcript.ytt_api")
    def test_fetch_transcript_disabled(self, mock_ytt_api):
        mock_ytt_api.list.side_effect = Exception("TranscriptsDisabled for abc")
        with self.assertRaises(TranscriptDisabledError):
            self.service.fetch_by_id("abc12345678")

    @patch("services.transcript.ytt_api")
    def test_fetch_no_transcript_found(self, mock_ytt_api):
        mock_ytt_api.list.side_effect = NoTranscriptFound("abc", ["en"], {})
        with self.assertRaises(TranscriptNotFoundError):
            self.service.fetch_by_id("abc12345678")

    # --- Chunking ---

    def test_chunk_short_text(self):
        text = "A short text that fits in one chunk."
        chunks = self.service._chunk_text(text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_chunk_long_text(self):
        # Generate text longer than MAX_TRANSCRIPT_CHARS
        text = "Hello World. " * 10000
        chunks = self.service._chunk_text(text)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), len(text))

    # --- Timestamp formatting ---

    def test_format_with_timestamps(self):
        entries = [
            {"start": 0.0, "text": "Hello"},
            {"start": 65.0, "text": "World"},
        ]
        result = self.service._format_with_timestamps(entries)
        self.assertIn("[00:00]", result)
        self.assertIn("[01:05]", result)
        self.assertIn("Hello", result)
        self.assertIn("World", result)


if __name__ == "__main__":
    unittest.main()

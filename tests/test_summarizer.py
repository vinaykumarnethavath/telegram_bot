"""
Tests for SummarizerService (mocked Groq client).
"""

import unittest
from unittest.mock import patch, MagicMock
from services.summarizer import SummarizerService, Summary


MOCK_SUMMARY_TEXT = """🎥 *Video Title*: Test Video

📌 *5 Key Points*:
1. Point one
2. Point two
3. Point three
4. Point four
5. Point five

⏱ *Important Timestamps*:
- [00:10] — Introduction

🧠 *Core Takeaway*:
This is the main insight of the video."""


def _make_mock_client(text: str):
    """Return a Groq-shaped mock client whose completions.create returns text."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = text
    return mock_client


class TestSummarizerService(unittest.TestCase):

    def setUp(self):
        self.service = SummarizerService()

    @patch("services.summarizer.get_groq_client")
    def test_summarize_single_chunk(self, mock_get_client):
        mock_get_client.return_value = _make_mock_client(MOCK_SUMMARY_TEXT)

        result = self.service.summarize(
            video_id="abc123",
            title="Test Video",
            chunks=["Short transcript that fits in one chunk."],
            language="en",
        )
        self.assertIsInstance(result, Summary)
        self.assertEqual(result.video_id, "abc123")
        self.assertEqual(result.video_title, "Test Video")
        self.assertIn("Key Points", result.text)
        mock_get_client.return_value.chat.completions.create.assert_called_once()

    @patch("services.summarizer.get_groq_client")
    def test_summarize_multiple_chunks_map_reduce(self, mock_get_client):
        mock_get_client.return_value = _make_mock_client(MOCK_SUMMARY_TEXT)

        result = self.service.summarize(
            video_id="def456",
            title="Long Video",
            chunks=["Chunk one content", "Chunk two content", "Chunk three content"],
            language="en",
        )
        self.assertIsInstance(result, Summary)
        # Map-reduce: 3 chunk partial summaries + 1 merge = 4 LLM calls
        self.assertEqual(
            mock_get_client.return_value.chat.completions.create.call_count, 4
        )

    @patch("services.summarizer.get_groq_client")
    def test_language_param_used(self, mock_get_client):
        mock_get_client.return_value = _make_mock_client(MOCK_SUMMARY_TEXT)

        self.service.summarize(
            video_id="ghi789",
            title="Hindi Video",
            chunks=["some transcript"],
            language="hi",
        )
        call_args = mock_get_client.return_value.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_msg = messages[1]["content"]
        self.assertIn("Hindi", user_msg)

    @patch("services.summarizer.get_groq_client")
    def test_summary_has_language(self, mock_get_client):
        mock_get_client.return_value = _make_mock_client(MOCK_SUMMARY_TEXT)
        result = self.service.summarize("x", "X", ["text"], language="kn")
        self.assertEqual(result.language, "kn")


if __name__ == "__main__":
    unittest.main()

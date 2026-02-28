"""
Tests for QAService (mocked Groq client).
"""

import unittest
from unittest.mock import patch, MagicMock
from services.qa import QAService


def _make_mock_client(text: str):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = text
    return mock_client


class TestQAService(unittest.TestCase):

    def setUp(self):
        self.service = QAService()

    @patch("services.qa.get_groq_client")
    def test_answer_with_relevant_info(self, mock_get_client):
        mock_get_client.return_value = _make_mock_client(
            "The pricing is $10/month, as stated in the video."
        )
        answer = self.service.answer(
            question="What is the pricing?",
            transcript="The product costs $10 per month and includes unlimited access.",
            title="Product Demo",
            qa_history=[],
            language="en",
        )
        self.assertIn("pricing", answer.lower())

    @patch("services.qa.get_groq_client")
    def test_answer_not_in_transcript(self, mock_get_client):
        mock_get_client.return_value = _make_mock_client(
            "❌ This topic is not covered in the video."
        )
        answer = self.service.answer(
            question="What is the CEO's name?",
            transcript="This is a video about machine learning algorithms.",
            title="ML Course",
            qa_history=[],
            language="en",
        )
        self.assertIn("not covered", answer)

    @patch("services.qa.get_groq_client")
    def test_qa_history_used(self, mock_get_client):
        mock_get_client.return_value = _make_mock_client(
            "As I mentioned, the pricing is $10/month."
        )
        history = [{"q": "Tell me about the product", "a": "It is a SaaS platform."}]
        self.service.answer(
            question="What about pricing?",
            transcript="Product costs $10/month.",
            title="Demo",
            qa_history=history,
            language="en",
        )
        call_args = mock_get_client.return_value.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_msg = messages[1]["content"]
        self.assertIn("Tell me about the product", user_msg)

    def test_relevant_excerpt_short_transcript(self):
        short_text = "This is a short transcript about AI."
        excerpt = self.service._get_relevant_excerpt("What is this about?", short_text)
        self.assertEqual(excerpt, short_text)

    def test_format_history_empty(self):
        result = self.service._format_history([])
        self.assertIn("No previous", result)

    def test_format_history_with_turns(self):
        history = [{"q": "Q1", "a": "A1"}, {"q": "Q2", "a": "A2"}]
        result = self.service._format_history(history)
        self.assertIn("Q1", result)
        self.assertIn("A2", result)


if __name__ == "__main__":
    unittest.main()

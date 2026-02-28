import unittest
from unittest.mock import patch, MagicMock
from groq import RateLimitError
from services.summarizer import SummarizerService
from services.analysis import AnalysisService

class TestFallback(unittest.TestCase):
    @patch("services.summarizer.get_groq_client")
    def test_summarizer_fallback(self, mock_get_client):
        # Setup mock to fail on first call and succeed on second
        mock_client = MagicMock()
        
        # Create a mock RateLimitError
        # (RateLimitError usually needs response, message etc, but we'll simulate the catch)
        mock_429 = RateLimitError(
            message="Rate limit reached",
            response=MagicMock(status_code=429),
            body={}
        )
        
        # Side effect: first call raises 429, second call returns success
        mock_client.chat.completions.create.side_effect = [
            mock_429,
            MagicMock(choices=[MagicMock(message=MagicMock(content="Fallback Summary"))])
        ]
        
        mock_get_client.return_value = mock_client
        
        svc = SummarizerService()
        result = svc._call_llm_with_fallback("system", "user")
        
        self.assertEqual(result, "Fallback Summary")
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)
        
        # Check models used
        calls = mock_client.chat.completions.create.call_args_list
        self.assertEqual(calls[0][1]['model'], "llama-3.3-70b-versatile")
        self.assertEqual(calls[1][1]['model'], "llama-3.1-8b-instant")

    @patch("services.analysis.get_groq_client")
    def test_analysis_fallback(self, mock_get_client):
        mock_client = MagicMock()
        mock_429 = RateLimitError(
            message="Rate limit reached",
            response=MagicMock(status_code=429),
            body={}
        )
        
        mock_client.chat.completions.create.side_effect = [
            mock_429,
            MagicMock(choices=[MagicMock(message=MagicMock(content="Fallback Analysis"))])
        ]
        
        mock_get_client.return_value = mock_client
        
        svc = AnalysisService()
        result = svc._call_llm_with_fallback("user prompt")
        
        self.assertEqual(result, "Fallback Analysis")
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)

if __name__ == "__main__":
    unittest.main()

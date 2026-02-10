"""Tests for Gemini API retry utility."""

from unittest.mock import MagicMock, patch

import pytest

from src.gemini_retry import gemini_retry


class TestGeminiRetry:
    """Tests for gemini_retry()."""

    def test_success_no_retry(self):
        """Successful call returns immediately, no retry."""
        fn = MagicMock(return_value="ok")
        result = gemini_retry(fn)
        assert result == "ok"
        assert fn.call_count == 1

    @patch("src.gemini_retry.time.sleep")
    def test_retry_on_503(self, mock_sleep):
        """503 error triggers retry, succeeds on 2nd attempt."""
        fn = MagicMock(side_effect=[Exception("503 Service Unavailable"), "ok"])
        result = gemini_retry(fn, max_retries=3, base_wait=1)
        assert result == "ok"
        assert fn.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch("src.gemini_retry.time.sleep")
    def test_retry_on_429(self, mock_sleep):
        """429 rate limit triggers retry."""
        fn = MagicMock(side_effect=[Exception("429 RESOURCE_EXHAUSTED"), "ok"])
        result = gemini_retry(fn, max_retries=3, base_wait=1)
        assert result == "ok"
        assert fn.call_count == 2

    @patch("src.gemini_retry.time.sleep")
    def test_retry_on_unavailable(self, mock_sleep):
        """UNAVAILABLE string in error triggers retry."""
        fn = MagicMock(side_effect=[Exception("UNAVAILABLE"), "ok"])
        result = gemini_retry(fn, max_retries=2, base_wait=1)
        assert result == "ok"

    @patch("src.gemini_retry.time.sleep")
    def test_max_retries_exceeded(self, mock_sleep):
        """All retries exhausted raises the exception."""
        fn = MagicMock(side_effect=Exception("503 error"))
        with pytest.raises(Exception, match="503 error"):
            gemini_retry(fn, max_retries=3, base_wait=1)
        assert fn.call_count == 3

    def test_non_retryable_error_raises_immediately(self):
        """Non-retryable errors raise without retry."""
        fn = MagicMock(side_effect=ValueError("invalid input"))
        with pytest.raises(ValueError, match="invalid input"):
            gemini_retry(fn, max_retries=3)
        assert fn.call_count == 1

    @patch("src.gemini_retry.time.sleep")
    def test_exponential_backoff(self, mock_sleep):
        """Wait time doubles each retry."""
        fn = MagicMock(side_effect=[
            Exception("503"), Exception("503"), "ok"
        ])
        result = gemini_retry(fn, max_retries=3, base_wait=2)
        assert result == "ok"
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2)   # 2 * 2^0
        mock_sleep.assert_any_call(4)   # 2 * 2^1

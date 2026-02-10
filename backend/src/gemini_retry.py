"""Shared Gemini API retry utility."""

import time
import logging

logger = logging.getLogger(__name__)


def gemini_retry(fn, max_retries=3, base_wait=2):
    """Retry fn() on Gemini 503/429 errors with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            err = str(e)
            retryable = any(code in err for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "disconnected", "RemoteProtocolError"))
            if retryable and attempt < max_retries - 1:
                wait = base_wait * (2 ** attempt)
                logger.warning(f"Gemini API error, retry {attempt+1}/{max_retries} in {wait}s: {e}")
                time.sleep(wait)
                continue
            raise

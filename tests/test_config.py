"""Unit tests for FaultSense application configuration and secret masking."""

import os
import unittest
from unittest.mock import patch

from config.settings import Settings, get_settings


class TestSettings(unittest.TestCase):
    """Verifies configuration loading, validation, and secret protection."""

    def test_default_settings(self):
        """Settings should load defaults and construct necessary paths."""
        settings = get_settings()
        self.assertEqual(settings.app_name, "FaultSense")
        self.assertTrue(settings.data_dir.exists())
        self.assertTrue(settings.upload_dir.exists())

    def test_demo_mode_auto_detected_when_no_api_key(self):
        """Demo mode should activate automatically when no LLM API key is present."""
        with patch.dict(os.environ, {"LLM_API_KEY": "", "OPENAI_API_KEY": "", "LLM_PROVIDER": "mock"}):
            s = Settings(llm_api_key=None, llm_provider="mock")
            self.assertTrue(s.is_demo_mode)
            notices = s.validate()
            self.assertTrue(any("Offline Demo Mode active" in n for n in notices))

    def test_safe_dict_masks_api_key(self):
        """get_safe_dict must never expose plaintext API keys."""
        s = Settings(llm_api_key="sk-proj-super-secret-1234567890", force_demo_mode=False)
        safe = s.get_safe_dict()
        self.assertNotIn("sk-proj-super-secret-1234567890", str(safe.values()))
        self.assertIn("****", safe["llm_api_key"])

    def test_safe_dict_when_no_key(self):
        """get_safe_dict should return '(Not Configured - Demo Mode)' when no key is set."""
        s = Settings(llm_api_key=None)
        safe = s.get_safe_dict()
        self.assertEqual(safe["llm_api_key"], "(Not Configured - Demo Mode)")


if __name__ == "__main__":
    unittest.main()

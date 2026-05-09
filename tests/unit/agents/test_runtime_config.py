from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from agents.common.runtime_config import load_llm_runtime_config


class RuntimeConfigTests(unittest.TestCase):
    def test_load_config_supports_direct_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "llm_config.local.json"
            path.write_text(
                json.dumps(
                    {
                        "enabled": True,
                        "api_key": "sk-local",
                        "api_key_env": "IGNORED_ENV",
                    }
                ),
                encoding="utf-8",
            )
            config = load_llm_runtime_config(path)
            self.assertTrue(config.enabled)
            self.assertEqual(config.api_key, "sk-local")
            self.assertEqual(config.api_key_env, "IGNORED_ENV")

    def test_env_override_for_direct_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "llm_config.local.json"
            path.write_text("{}", encoding="utf-8")
            previous = os.environ.get("FORGEFLOW_LLM_API_KEY")
            os.environ["FORGEFLOW_LLM_API_KEY"] = "sk-env"
            try:
                config = load_llm_runtime_config(path)
            finally:
                if previous is None:
                    os.environ.pop("FORGEFLOW_LLM_API_KEY", None)
                else:
                    os.environ["FORGEFLOW_LLM_API_KEY"] = previous
            self.assertEqual(config.api_key, "sk-env")


if __name__ == "__main__":
    unittest.main()

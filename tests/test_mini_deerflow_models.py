from __future__ import annotations

import unittest
from unittest.mock import patch

from langchain_core.language_models.chat_models import BaseChatModel

from mini_deerflow.config import ModelProfile, ModelSettings
from mini_deerflow.models import ModelConfigurationError, create_model


class ModelFactoryTests(unittest.TestCase):
    def test_offline_profile_creates_a_local_chat_model(self) -> None:
        model = create_model(ModelSettings(profile=ModelProfile.OFFLINE))

        self.assertIsInstance(model, BaseChatModel)
        self.assertEqual(model.invoke("你好").content, "这是离线模型的确定性回答。")

    @patch.dict("os.environ", {}, clear=True)
    def test_deepseek_profile_fails_before_network_without_a_key(self) -> None:
        with self.assertRaisesRegex(ModelConfigurationError, "DEEPSEEK_API_KEY"):
            create_model(ModelSettings(profile=ModelProfile.DEEPSEEK))


if __name__ == "__main__":
    unittest.main()

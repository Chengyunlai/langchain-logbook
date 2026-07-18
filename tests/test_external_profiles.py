from __future__ import annotations

import os

import pytest


PROFILE = os.getenv("LANGCHAIN_LOGBOOK_PROFILE", "offline")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
EXTERNAL_ENABLED = PROFILE == "integration" and bool(DEEPSEEK_API_KEY)


@pytest.mark.integration
@pytest.mark.skipif(
    not EXTERNAL_ENABLED,
    reason="需要 LANGCHAIN_LOGBOOK_PROFILE=integration 与 DEEPSEEK_API_KEY",
)
def test_deepseek_chat_model_can_answer_a_smoke_request() -> None:
    """最小真实供应商冒烟测试；默认离线门禁只收集并明确跳过它。"""
    from langchain.chat_models import init_chat_model

    model = init_chat_model("deepseek:deepseek-chat", temperature=0)
    response = model.invoke("只回答 OK")

    assert response.content

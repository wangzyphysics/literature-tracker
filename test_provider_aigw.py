import os
from unittest import mock
from ai_summarizer import build_provider, OpenRouterProvider


def test_aigw_routes_to_openai_compatible():
    with mock.patch.dict(os.environ, {"AI_BASE_URL": "https://aigw.sotatts.online/v1"}):
        p = build_provider("aigw", "sk-test", model="gpt-5.5")
    assert isinstance(p, OpenRouterProvider)
    assert p.model == "gpt-5.5"
    assert p.base_url.endswith("/chat/completions")
    assert "aigw.sotatts.online" in p.base_url

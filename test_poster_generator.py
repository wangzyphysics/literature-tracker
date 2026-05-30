import os, tempfile
from unittest import mock
import poster_generator
from poster_generator import extract_elements, build_background_prompt, generate_poster

def test_extract_elements_parses_json():
    class P:
        def call_api(self, prompt):
            return '```json\n{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v"}\n```'
    el = extract_elements({"title": "T"}, "body", provider=P())
    assert el["创新方法"] == "m" and el["应用价值"] == "v"

def test_extract_elements_returns_none_on_bad_json():
    class P:
        def call_api(self, prompt): return "not json at all"
    assert extract_elements({"title": "T"}, "body", provider=P()) is None

def test_extract_elements_none_provider():
    assert extract_elements({"title": "T"}, "body", provider=None) is None

def test_background_prompt_is_text_free_memphis():
    p = build_background_prompt({"研究问题": "q"})
    assert "Memphis" in p
    assert "16:9" in p
    assert "no text" in p.lower() or "without text" in p.lower()

def test_generate_poster_calls_image():
    class P:
        def call_api(self, prompt):
            return '{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v"}'
    d = tempfile.mkdtemp()
    with mock.patch.object(poster_generator, "generate_and_save",
                           side_effect=lambda prompt, out_path, **k: out_path):
        res = generate_poster({"title": "T", "doc_id": "d1"}, "body", provider=P(), out_dir=d)
    assert res["elements"]["创新方法"] == "m"
    assert res["image"].endswith("d1.webp")

def test_generate_poster_none_when_extract_fails():
    class P:
        def call_api(self, prompt): return "garbage"
    assert generate_poster({"title": "T", "doc_id": "d1"}, "body", provider=P()) is None

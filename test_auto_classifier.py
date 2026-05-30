from auto_classifier import classify

def test_rule_hit_skips_llm():
    a = {"title": "Altermagnetic spin splitting", "summary": "antiferromagnet"}
    # provider must NOT be called when a rule matches; pass a provider that explodes if used
    class Explode:
        def call_api(self, p): raise AssertionError("provider should not be called")
    assert classify(a, provider=Explode()) == "磁性·自旋电子学"

def test_rule_miss_uses_llm_fallback():
    class P:
        def call_api(self, prompt): return "量子信息·计算"
    a = {"title": "Some ambiguous title", "summary": "vague"}
    assert classify(a, provider=P()) == "量子信息·计算"

def test_llm_returns_unknown_category_falls_back_to_other():
    class P:
        def call_api(self, prompt): return "天体物理"  # not in taxonomy
    a = {"title": "ambiguous", "summary": "vague"}
    assert classify(a, provider=P()) == "其他"

def test_no_provider_and_no_rule_returns_other():
    a = {"title": "ambiguous", "summary": "vague"}
    assert classify(a, provider=None) == "其他"

def test_llm_error_returns_other():
    class Boom:
        def call_api(self, p): raise Exception("down")
    a = {"title": "ambiguous", "summary": "vague"}
    assert classify(a, provider=Boom()) == "其他"

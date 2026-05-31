import os, tempfile
from unittest import mock
import run_deep

def test_process_date_enriches_aps():
    metas = [{"title": "ML potential for perovskite", "journal": "PRL",
              "has_full_text": True, "markdown_oss_key": "k", "doc_id": "d1",
              "summary": "graph neural network"}]
    class FakeClient:
        def fetch_metadata(self, d): return metas
        def fetch_markdown(self, m): return "# Paper\nbody"
    class FakeProv:
        def call_api(self, p):
            # poster extraction prompt contains JSON/研究问题; deep-read prompt does not
            if ("研究问题" in p) or ("JSON" in p):
                return '{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v"}'
            return "## 精读\n内容"
    d = tempfile.mkdtemp()
    with mock.patch.object(run_deep, "generate_and_save",
                           side_effect=lambda prompt, out_path, **k: out_path):
        out, _used = run_deep.process_date("2026-05-28", client=FakeClient(),
                                    provider=FakeProv(), out_dir=d)
    assert len(out) == 1
    assert out[0]["deep_analysis"]
    assert out[0]["category"] in ("AI×物理", "AI×化学·材料")
    assert out[0]["poster"]["elements"]["创新方法"] == "m"

def test_process_date_skips_non_fulltext():
    metas = [{"title": "x", "has_full_text": False, "doc_id": "d2"}]
    class FakeClient:
        def fetch_metadata(self, d): return metas
        def fetch_markdown(self, m): return ""
    class FakeProv:
        def call_api(self, p): return "{}"
    out, _used = run_deep.process_date("2026-05-28", client=FakeClient(), provider=FakeProv())
    assert out == []

def test_prune_images_removes_old(tmpdir=None):
    import datetime
    d = tempfile.mkdtemp()
    old = os.path.join(d, "old.webp"); new = os.path.join(d, "new.webp")
    open(old, "wb").write(b"x"); open(new, "wb").write(b"y")
    # backdate 'old' 100 days
    past = (datetime.datetime.now() - datetime.timedelta(days=100)).timestamp()
    os.utime(old, (past, past))
    run_deep.prune_images(window_days=60, dirs=(d,))
    assert not os.path.exists(old)
    assert os.path.exists(new)

def test_enrich_arxiv_core_adds_image():
    import run_deep, tempfile
    from unittest import mock
    d = tempfile.mkdtemp()
    items = [{"title": "ML potential for magnet", "summary": "neural network",
              "link": "http://z"}]
    with mock.patch.object(run_deep, "generate_and_save",
                           side_effect=lambda prompt, out_path, **k: out_path):
        out = run_deep.enrich_arxiv_core(items, out_dir=d)
    assert out[0]["image"].endswith(".webp")
    assert out[0]["category"]
    assert out[0]["source"] == "arxiv"

def test_enrich_arxiv_core_image_none_on_failure():
    import run_deep, tempfile
    from unittest import mock
    items = [{"title": "x", "link": "http://z"}]
    with mock.patch.object(run_deep, "generate_and_save",
                           side_effect=lambda prompt, out_path, **k: None):
        out = run_deep.enrich_arxiv_core(items, out_dir=tempfile.mkdtemp())
    assert out[0]["image"] is None


def test_process_date_reuses_cache():
    """已缓存(带 deep_analysis)的论文不重复调用 provider。"""
    metas = [{"title": "x", "has_full_text": True, "markdown_oss_key": "k",
              "doc_id": "d1", "summary": "s"}]
    class FakeClient:
        def fetch_metadata(self, d): return metas
        def fetch_markdown(self, m): raise AssertionError("should not fetch when cached")
    class Explode:
        def call_api(self, p): raise AssertionError("provider should not be called when cached")
    cache = {"d1": {"doc_id": "d1", "source": "APS", "deep_analysis": "## cached\n第五部分：创新评估 " + "x"*6000,
                    "category": "AI×物理", "poster": None}}
    out, _used = run_deep.process_date("2026-05-28", client=FakeClient(),
                                provider=Explode(), cache=cache)
    assert len(out) == 1
    assert out[0]["deep_analysis"].startswith("## cached")


def test_truncated_deep_is_retried():
    """缺第五部分(创新)的截断深读不算完成，应重新处理。"""
    metas = [{"title": "x", "has_full_text": True, "markdown_oss_key": "k",
              "doc_id": "d1", "summary": "s"}]
    class FakeClient:
        def fetch_metadata(self, d): return metas
        def fetch_markdown(self, m): return "# P\nbody"
    class FakeProv:
        def call_api(self, p):
            return '{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v"}' \
                   if ("研究问题" in p or "JSON" in p) else ("## 完整\n第五部分：创新评估 " + "y"*6000)
    import tempfile
    from unittest import mock
    # cached but truncated (no 创新, short) -> must be reprocessed
    cache = {"d1": {"doc_id": "d1", "deep_analysis": "## 截断在这里", "poster": None}}
    with mock.patch.object(run_deep, "generate_and_save",
                           side_effect=lambda prompt, out_path, **k: out_path):
        out, used = run_deep.process_date("2026-05-28", client=FakeClient(),
                                          provider=FakeProv(), out_dir=tempfile.mkdtemp(),
                                          cache=cache)
    assert used == 1  # 被当作 fresh 重处理
    assert "创新" in out[0]["deep_analysis"]


def test_process_date_respects_max_new_budget():
    metas = [{"title": "p%d" % i, "has_full_text": True, "markdown_oss_key": "k",
              "doc_id": "d%d" % i, "summary": "s"} for i in range(10)]
    class FakeClient:
        def fetch_metadata(self, d): return metas
        def fetch_markdown(self, m): return "# P\nbody"
    class FakeProv:
        def call_api(self, p):
            return '{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v"}' \
                   if ("研究问题" in p or "JSON" in p) else "## 精读"
    import tempfile
    from unittest import mock
    with mock.patch.object(run_deep, "generate_and_save",
                           side_effect=lambda prompt, out_path, **k: out_path):
        out, used = run_deep.process_date("2026-05-28", client=FakeClient(),
                                          provider=FakeProv(), out_dir=tempfile.mkdtemp(),
                                          max_new=3)
    assert used == 3
    assert len(out) == 3


def test_enrich_one_sets_title_zh_from_poster():
    import run_deep, tempfile
    from unittest import mock
    meta = {"title": "EN title", "has_full_text": True, "markdown_oss_key": "k", "doc_id": "d1"}
    class FakeClient:
        def fetch_markdown(self, m): return "# P\nbody"
    class P:
        def call_api(self, p):
            return ('{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v",'
                    '"title_zh":"中文标题","elements_en":{"method":"GNN"}}') if ("研究问题" in p or "JSON" in p) \
                   else "## 完整\n第五部分：创新评估 " + "y"*6000
    with mock.patch.object(run_deep, "generate_and_save", side_effect=lambda prompt, out_path, **k: out_path):
        rec = run_deep._enrich_one(meta, FakeClient(), P(), tempfile.mkdtemp())
    assert rec["title_zh"] == "中文标题"


def test_process_arxiv_tier2_enriches_and_budgets():
    import run_deep, tempfile
    from unittest import mock
    cands = [{"title": "ML for magnet", "abstract": "neural network spin", "link": "http://z%d" % i,
              "category": "AI×物理"} for i in range(5)]
    class P:
        def call_api(self, p):
            return ('{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v",'
                    '"title_zh":"标题","elements_en":{"method":"GNN"}}') if ("研究问题" in p or "JSON" in p) \
                   else "## 摘要级\n创新性判断 " + "z"*5200
    with mock.patch.object(run_deep, "generate_and_save", side_effect=lambda prompt, out_path, **k: out_path):
        out, used = run_deep.process_arxiv_tier2("2026-05-28", cands, P(),
                                                 out_dir=tempfile.mkdtemp(), max_new=3)
    assert used == 3
    assert sum(1 for x in out if x.get("deep_analysis")) == 3

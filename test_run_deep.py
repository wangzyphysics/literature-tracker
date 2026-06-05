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


def test_tier2_short_abstract_analysis_is_complete_not_reprocessed():
    # C2 regression: a concise (realistic) abstract analysis must count as complete,
    # else tier-2 gets reprocessed every run and exhausts the budget.
    import run_deep, tempfile
    from unittest import mock
    # realistic concise abstract analysis: ~400 chars (far below the 5000 full-text bar)
    short = ("## 核心概览\n" + "本文用图神经网络构建可迁移的原子间势，研究钙钛矿铁电相变。" * 6 +
             "\n## 创新性判断\n相对前人首次实现跨组分迁移。" * 2)
    assert 120 <= len(short) < 5000
    assert run_deep._deep_complete_abstract(short) is True
    assert run_deep._deep_complete(short) is False  # full-text bar would wrongly reject
    cands = [{"title": "P", "abstract": "abs", "link": "http://z", "category": "AI×物理"}]
    # A settled abstract-mode record (full-text retries exhausted) must NOT be reprocessed.
    cache = {"http://z": {"link": "http://z", "deep_analysis": short, "poster": {"image": "x.webp"},
                          "analysis_mode": "abstract", "ft_attempts": 3}}
    assert run_deep._tier2_complete(cache["http://z"]) is True
    class Explode:
        def call_api(self, p): raise AssertionError("provider must not be called for complete tier-2")
    with mock.patch.object(run_deep, "generate_and_save",
                           side_effect=AssertionError("no image regen for complete tier-2")):
        out, used = run_deep.process_arxiv_tier2("2026-05-28", cands, Explode(),
                                                 out_dir=tempfile.mkdtemp(), cache=cache)
    assert used == 0
    assert out[0]["deep_analysis"] == short


def test_tier2_complete_fulltext_done():
    import run_deep
    rec = {"deep_analysis": "## 深析\n第五部分：创新评估 " + "x" * 3500,
           "analysis_mode": "html", "ft_attempts": 1}
    assert run_deep._tier2_complete(rec) is True


def test_tier2_complete_pdf_done():
    import run_deep
    rec = {"deep_analysis": "创新评估 " + "y" * 3500, "analysis_mode": "pdf", "ft_attempts": 1}
    assert run_deep._tier2_complete(rec) is True


def test_tier2_complete_abstract_not_done_until_attempts_cap():
    import run_deep
    short = "## 概览\n创新性判断：" + "z" * 200  # 有"创新", >120, <3000
    assert run_deep._tier2_complete({"deep_analysis": short, "analysis_mode": "abstract", "ft_attempts": 1}) is False
    assert run_deep._tier2_complete({"deep_analysis": short, "analysis_mode": "abstract", "ft_attempts": 3}) is True


def test_tier2_complete_legacy_record_not_done():
    import run_deep
    legacy = {"deep_analysis": "## 概览\n创新性判断：" + "z" * 200}
    assert run_deep._tier2_complete(legacy) is False


def test_tier2_complete_empty_or_none():
    import run_deep
    assert run_deep._tier2_complete(None) is False
    assert run_deep._tier2_complete({"deep_analysis": ""}) is False


def test_tier2_complete_fulltext_too_short_not_done():
    import run_deep
    rec = {"deep_analysis": "创新 " + "x" * 100, "analysis_mode": "html", "ft_attempts": 1}
    assert run_deep._tier2_complete(rec) is False


def test_enrich_tier2_uses_fulltext_deepread_when_available():
    import run_deep, arxiv_fulltext, tempfile
    from unittest import mock
    cand = {"title": "ML for magnet", "abstract": "abs", "link": "https://arxiv.org/abs/2406.04520",
            "category": "AI×物理"}
    class P:
        def call_api(self, p):
            if ("研究问题" in p) or ("JSON" in p):
                return '{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v","title_zh":"标题"}'
            return "## 全文苏格拉底\n第五部分：创新评估 " + "z" * 3500
    with mock.patch.object(arxiv_fulltext, "fetch_fulltext", return_value=("FULLTEXT BODY " * 500, "html")), \
         mock.patch.object(run_deep, "generate_and_save", side_effect=lambda prompt, out_path, **k: out_path):
        rec = run_deep._enrich_arxiv_tier2_one(cand, P(), tempfile.mkdtemp())
    assert rec["analysis_mode"] == "html"
    assert "创新评估" in rec["deep_analysis"] and len(rec["deep_analysis"]) >= 3000
    assert rec["ft_attempts"] == 1
    assert run_deep._tier2_complete(rec) is True


def test_enrich_tier2_falls_back_to_abstract_and_increments_attempts():
    import run_deep, arxiv_fulltext, tempfile
    from unittest import mock
    cand = {"title": "P", "abstract": "neural network spin", "link": "https://arxiv.org/abs/2606.99999",
            "category": "AI×物理"}
    class P:
        def call_api(self, p):
            if ("研究问题" in p) or ("JSON" in p):
                return '{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v"}'
            return "## 摘要级\n创新性判断 " + "z" * 200
    cached = {"ft_attempts": 1}  # 此前已尝试 1 次
    with mock.patch.object(arxiv_fulltext, "fetch_fulltext", return_value=("", "")), \
         mock.patch.object(run_deep, "generate_and_save", side_effect=lambda prompt, out_path, **k: out_path):
        rec = run_deep._enrich_arxiv_tier2_one(cand, P(), tempfile.mkdtemp(), cached=cached)
    assert rec["analysis_mode"] == "abstract"
    assert rec["ft_attempts"] == 2


def test_enrich_tier2_returns_cached_when_complete():
    import run_deep, arxiv_fulltext
    from unittest import mock
    done = {"deep_analysis": "创新评估 " + "x" * 3500, "analysis_mode": "html", "ft_attempts": 1,
            "poster": {"image": "p.webp"}}
    with mock.patch.object(arxiv_fulltext, "fetch_fulltext",
                           side_effect=AssertionError("must not refetch a complete record")):
        rec = run_deep._enrich_arxiv_tier2_one({"link": "https://arxiv.org/abs/2406.04520"},
                                               provider=None, out_dir="x", cached=done)
    assert rec is done


def test_tier2_complete_caps_retries_on_empty_or_keywordless_text():
    # B1 regression: empty / keyword-less analysis MUST settle at the attempt cap,
    # else the record is reprocessed every run and drains the shared budget forever.
    import run_deep
    assert run_deep._tier2_complete({"deep_analysis": "", "ft_attempts": 5}) is True       # settled empty
    assert run_deep._tier2_complete({"deep_analysis": "无关键词的文本", "ft_attempts": 3}) is True
    # below the cap → still retried (eligible for full-text upgrade)
    assert run_deep._tier2_complete({"deep_analysis": "", "ft_attempts": 2}) is False
    assert run_deep._tier2_complete({"deep_analysis": "短文本", "analysis_mode": "abstract", "ft_attempts": 1}) is False

from arxiv_fulltext import arxiv_id


def test_arxiv_id_from_abs():
    assert arxiv_id("https://arxiv.org/abs/2606.04803") == "2606.04803"


def test_arxiv_id_from_pdf_and_html():
    assert arxiv_id("https://arxiv.org/pdf/2606.04803") == "2606.04803"
    assert arxiv_id("https://arxiv.org/html/2606.04803") == "2606.04803"


def test_arxiv_id_strips_version():
    assert arxiv_id("https://arxiv.org/abs/2606.04803v2") == "2606.04803"


def test_arxiv_id_bare_and_5digit():
    assert arxiv_id("2406.04520") == "2406.04520"
    assert arxiv_id("https://arxiv.org/abs/2501.01234") == "2501.01234"


def test_arxiv_id_old_style():
    assert arxiv_id("https://arxiv.org/abs/cond-mat/0703470") == "cond-mat/0703470"


def test_arxiv_id_empty_or_nonarxiv():
    assert arxiv_id("") == ""
    assert arxiv_id(None) == ""
    assert arxiv_id("https://doi.org/10.1103/abc") == ""


def test_arxiv_id_arxiv_prefix():
    assert arxiv_id("arXiv:2606.04803") == "2606.04803"
    assert arxiv_id("arxiv:2606.04803v3") == "2606.04803"


def test_html_to_text_extracts_visible_and_skips_script_style():
    from arxiv_fulltext import html_to_text
    html = ("<html><head><style>.x{color:red}</style>"
            "<script>var a=1;</script></head><body>"
            "<nav>导航不要</nav><p>第一段正文 alpha</p>"
            "<div>第二段 beta</div><footer>页脚不要</footer></body></html>")
    txt = html_to_text(html)
    assert "第一段正文 alpha" in txt
    assert "第二段 beta" in txt
    assert "color:red" not in txt
    assert "var a=1" not in txt
    assert "导航不要" not in txt
    assert "页脚不要" not in txt


def test_html_to_text_empty():
    from arxiv_fulltext import html_to_text
    assert html_to_text("") == ""
    assert html_to_text("<body></body>").strip() == ""


def test_fetch_fulltext_html_hit():
    import arxiv_fulltext as af
    long_body = "正文内容 " * 1000  # >4000 chars
    af._get_text = lambda url: f"<body><p>{long_body}</p></body>" if "html" in url else None
    af._get_bytes = lambda url: (_ for _ in ()).throw(AssertionError("PDF must not be fetched when HTML suffices"))
    text, mode = af.fetch_fulltext("https://arxiv.org/abs/2406.04520")
    assert mode == "html"
    assert "正文内容" in text


def test_fetch_fulltext_html_too_short_falls_to_pdf():
    import arxiv_fulltext as af
    af._get_text = lambda url: "<body><p>太短的摘要占位</p></body>"  # < min_chars
    af._get_bytes = lambda url: b"%PDF-FAKE"
    af.extract_pdf_text = lambda b: "PDF 提取的全文 " * 1000  # >4000
    text, mode = af.fetch_fulltext("https://arxiv.org/abs/2606.04803")
    assert mode == "pdf"
    assert "PDF 提取的全文" in text


def test_fetch_fulltext_all_fail_returns_empty():
    import arxiv_fulltext as af
    af._get_text = lambda url: None
    af._get_bytes = lambda url: None
    assert af.fetch_fulltext("https://arxiv.org/abs/2606.04803") == ("", "")


def test_fetch_fulltext_truncates_to_max_chars():
    import arxiv_fulltext as af
    af._get_text = lambda url: "<body><p>" + ("a" * 100000) + "</p></body>"
    af._get_bytes = lambda url: None
    text, mode = af.fetch_fulltext("https://arxiv.org/abs/2406.04520", max_chars=5000)
    assert mode == "html" and len(text) <= 5000


def test_fetch_fulltext_non_arxiv_returns_empty():
    import arxiv_fulltext as af
    assert af.fetch_fulltext("https://doi.org/10.1/x") == ("", "")



def test_fetch_fulltext_short_pdf_also_rejected():
    import arxiv_fulltext as af
    af._get_text = lambda url: "<body><p>太短占位</p></body>"  # HTML below gate
    af._get_bytes = lambda url: b"%PDF"
    af.extract_pdf_text = lambda b: "短"  # PDF extraction also below min_chars
    assert af.fetch_fulltext("https://arxiv.org/abs/2606.04803") == ("", "")


if __name__ == "__main__":
    import inspect
    # Re-import fresh module for the network tests that monkeypatch module globals;
    # run them last so patches don't leak into the pure-function tests.
    g = dict(globals())
    fns = [(k, v) for k, v in g.items() if k.startswith("test_") and inspect.isfunction(v)]
    for name, f in fns:
        f()
    print(f"[OK] arxiv_fulltext {len(fns)} tests")

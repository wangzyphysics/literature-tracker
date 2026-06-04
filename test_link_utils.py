from link_utils import normalize_link


def test_bare_doi_becomes_url():
    assert normalize_link("10.1103/766t-tqsy") == "https://doi.org/10.1103/766t-tqsy"


def test_http_link_unchanged():
    assert normalize_link("http://arxiv.org/abs/2601.001") == "http://arxiv.org/abs/2601.001"
    assert normalize_link("https://doi.org/10.1/x") == "https://doi.org/10.1/x"


def test_empty_returns_empty():
    assert normalize_link("") == ""
    assert normalize_link(None) == ""


if __name__ == "__main__":
    test_bare_doi_becomes_url()
    test_http_link_unchanged()
    test_empty_returns_empty()
    print("[OK] link_utils")

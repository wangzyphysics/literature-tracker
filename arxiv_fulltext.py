"""arxiv 全文获取：HTML(arxiv/ar5iv) 优先，PDF(pdfminer) 兜底。

网络层 `_get_text` / `_get_bytes` / `extract_pdf_text` 为模块级函数，
测试通过 monkeypatch 它们注入内容，绝不触网。
"""
import re
import io
from html.parser import HTMLParser

_NEW_ID = re.compile(r'(\d{4}\.\d{4,5})')
_OLD_ID = re.compile(r'arxiv\.org/(?:abs|pdf|html)/([a-z\-]+/\d{7})', re.I)

_UA = "literature-tracker/1.0 (+https://github.com/Hongyu-yu/literature-tracker)"
MIN_FULLTEXT_CHARS = 4000


def arxiv_id(link):
    """从 arxiv 链接/裸 ID 解析 arxiv 标识；非 arxiv → ""。"""
    s = (link or "").strip()
    if not s:
        return ""
    m = _OLD_ID.search(s)
    if m:
        return m.group(1)
    # 仅当像 arxiv 链接 / arXiv: 前缀 / 裸 ID 时才接受新式数字 ID（避免误抓 DOI 里的数字）
    if "arxiv.org" in s or s.lower().startswith("arxiv:") or re.fullmatch(r'\d{4}\.\d{4,5}(v\d+)?', s):
        m = _NEW_ID.search(s)
        if m:
            return m.group(1)
    return ""


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer", "noscript"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            s = data.strip()
            if s:
                self.parts.append(s)


def html_to_text(html):
    p = _TextExtractor()
    try:
        p.feed(html or "")
    except Exception:
        pass
    return re.sub(r'[ \t]+', ' ', " ".join(p.parts)).strip()


def _get_text(url):
    """GET → 文本；失败 → None。可被测试 monkeypatch。"""
    try:
        import requests
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=30, allow_redirects=True)
        if r.status_code == 200 and r.text:
            return r.text
    except Exception as e:
        print(f"⚠️ arxiv html GET failed {url}: {e}")
    return None


def _get_bytes(url):
    """GET → bytes；失败 → None。可被测试 monkeypatch。"""
    try:
        import requests
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=45, allow_redirects=True)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception as e:
        print(f"⚠️ arxiv pdf GET failed {url}: {e}")
    return None


def extract_pdf_text(pdf_bytes):
    """pdfminer.six 提取 PDF 文本；缺包/失败 → ""。可被测试 monkeypatch。"""
    if not pdf_bytes:
        return ""
    try:
        from pdfminer.high_level import extract_text
        return extract_text(io.BytesIO(pdf_bytes)) or ""
    except Exception as e:
        print(f"⚠️ pdf extract failed: {e}")
        return ""


def fetch_fulltext(link, max_chars=40000, min_chars=MIN_FULLTEXT_CHARS):
    """返回 (text, mode)；mode ∈ {"html","pdf",""}。失败/非 arxiv → ("","")。"""
    aid = arxiv_id(link)
    if not aid:
        return ("", "")
    for url in (f"https://arxiv.org/html/{aid}", f"https://ar5iv.org/abs/{aid}"):
        html = _get_text(url)
        if html:
            txt = html_to_text(html)
            if len(txt) >= min_chars:
                return (txt[:max_chars], "html")
    pdf = _get_bytes(f"https://arxiv.org/pdf/{aid}")
    if pdf:
        txt = extract_pdf_text(pdf)
        if len(txt) >= min_chars:
            return (txt[:max_chars], "pdf")
    return ("", "")

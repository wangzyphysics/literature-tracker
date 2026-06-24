"""
配置文件 - RSS文献追踪系统
"""

# RSS订阅源列表
RSS_FEEDS = [
    "http://feeds.aps.org/rss/allsuggestions.xml",
    "http://feeds.aps.org/rss/recent/prl.xml",
    "http://feeds.aps.org/rss/recent/prx.xml",
    "http://feeds.aps.org/rss/recent/physics.xml",
    "http://feeds.aps.org/rss/recent/rmp.xml",
    "https://phys.org/rss-feed/physics-news/",
    "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science",
    "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=sciadv",
    "https://www.nature.com/nature.rss",
    "https://www.nature.com/natcomputsci.rss",
    "https://www.nature.com/nchem.rss",
    "https://www.nature.com/natmachintell.rss",
    "https://www.nature.com/natrevmats.rss",
    "https://www.nature.com/nphys.rss",
    "https://www.nature.com/natrevchem.rss",
    "https://www.nature.com/natelectron.rss",
    "https://www.nature.com/nnano.rss",
    "https://www.nature.com/nphoton.rss",
    "https://www.nature.com/natrevphys.rss",
    "https://www.nature.com/ncomms.rss",
    "https://www.nature.com/npjcompumats.rss",
    "https://academic.oup.com/rss/site_5332/3198.xml",
    "https://rss.sciencedirect.com/publication/science/20959273",
    "https://pubs.acs.org/action/showFeed?type=axatoc&feed=rss&jc=jacsat",  # JACS（feedburner 源已废弃，改用 pubs.acs.org）
    "https://pubs.acs.org/action/showFeed?type=axatoc&feed=rss&jc=ancac3",
    "https://onlinelibrary.wiley.com/action/showFeed?jc=15213773&type=etoc&feed=rss",
    "https://pubs.acs.org/action/showFeed?type=axatoc&feed=rss&jc=nalefd",
    "https://www.annualreviews.org/action/showFeed?ui=45mu4&mi=3fndc3&ai=68t8&jc=conmatphys&type=etoc&feed=atom",
    "https://www.annualreviews.org/action/showFeed?ui=45mu4&mi=3fndc3&ai=sy&jc=physchem&type=etoc&feed=atom",
    "https://pubs.acs.org/action/showFeed?type=axatoc&feed=rss&jc=jpclcd",
    "https://www.pnas.org/rss/Physics.xml",
    "https://www.pnas.org/rss/Applied_Physical_Sciences.xml",
    "https://pubs.acs.org/action/showFeed?type=axatoc&feed=rss&jc=jctcce",
    "https://aip.scitation.org/action/showFeed?type=etoc&feed=rss&jc=jcp",
    "http://aip.scitation.org/action/showFeed?type=etoc&feed=rss&jc=apl",
    "https://pubs.aip.org/rss/site_1000043/1000024.xml",
    "http://feeds.aps.org/rss/recent/prxenergy.xml",
    "http://feeds.aps.org/rss/recent/prmaterials.xml",
    "http://feeds.aps.org/rss/recent/prresearch.xml",
    "http://feeds.aps.org/rss/recent/prb.xml",
    "https://pubs.acs.org/action/showFeed?type=axatoc&feed=rss&jc=chreay",
    # feedburner ACS 源已废弃(只返回"feed has changed"占位)；nalefd/achre4 上文已有 pubs.acs.org 等价源，physicstodaynews 无替代，一并移除
    "https://iopscience.iop.org/journal/rss/2632-2153",
    "https://onlinelibrary.wiley.com/action/showFeed?jc=15214095&type=etoc&feed=rss",
    "https://onlinelibrary.wiley.com/action/showFeed?jc=16163028&type=etoc&feed=rss",
    "https://onlinelibrary.wiley.com/action/showFeed?jc=21983844&type=etoc&feed=rss",
    "https://rss.arxiv.org/rss/cond-mat",
    "https://rss.arxiv.org/rss/physics",
    # AI 相关 arXiv 分类（用于 AI×材料/物理/化学交叉，提升召回）
    "https://rss.arxiv.org/rss/cs.LG",
    "https://rss.arxiv.org/rss/stat.ML",
    "https://rss.arxiv.org/rss/cs.AI",
    "https://chemrxiv.org/engage/rss/chemrxiv",
    "https://www.researchsquare.com/rss.xml",
    "https://rss.arxiv.org/rss/cond-mat.supr-con+cond-mat.mtrl-sci+cond-mat.str-el+physics.comp-ph+physics.chem-ph",
    "https://feeds.rsc.org/rss/dd",  # Digital Discovery (RSC - AI for chemistry)
    "https://rss.sciencedirect.com/publication/science/09270256",  # Computational Materials Science
    "https://rss.sciencedirect.com/publication/science/00104655",  # Computer Physics Communications
    "https://www.nature.com/npjquantmats.rss",  # npj Quantum Materials
    "https://rss.sciencedirect.com/publication/science/13697021",  # Materials Today
    "https://www.nature.com/npj2dmaterials.rss",  # npj 2D Materials and Applications
    "http://feeds.aps.org/rss/recent/prapplied.xml",  # Physical Review Applied
    # ========== 2区期刊（仅保留指定）==========
    "https://aip.scitation.org/action/showFeed?type=etoc&feed=rss&jc=jap",  # Journal of Applied Physics (JAP)
    "https://rss.sciencedirect.com/publication/science/00092614",  # Chemical Physics Letters (CPL)
]

# 多用户关键词配置
# 每个用户可以定义自己的关键词列表，用于在网页上筛选相关文献
USER_KEYWORDS = {
    "于宏宇": [
        "ferro",
        "machine",
        "learn",
        "magne",
        "neural",
        "network",
        "potential",
        "hamiltonian",
    ],
    "朱海燕": [
        "twist",
        "magne",
        "moire",
        "multiferroics",
        "magnetoelectric coupling",
        "CrSBr",
        "altermagnet",
        "ferro",
        "CrTe",
        "magnetic nanotube",
        "topological curvature",
        "curvature-driven",
    ],
    "戴智浩": [
        "symmetry",
        "group theory",
        "altermagnet",
        "ferromagnetoelectric",
        "multiferroics",
        "compensated magnet",
        "unconventional magnet",
    ],
}

# 关键词列表（保持向后兼容，使用于宏宇的关键词）
KEYWORDS = USER_KEYWORDS.get("于宏宇", [])

import os

# 加载本地配置 config.local.py（已 gitignore）。
# 注意：不能用 `from config.local import ...` —— config.py 是单文件而非包，
# 那种写法永远 ModuleNotFoundError。改用按文件路径加载，单文件布局下才生效。
_local_config = None
try:
    import importlib.util as _ilu

    _local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.local.py")
    if os.path.exists(_local_path):
        _spec = _ilu.spec_from_file_location("config_local", _local_path)
        _local_config = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_local_config)
except Exception as _e:  # 本地配置坏掉不应阻塞主流程（CI 走环境变量）
    print(f"⚠️ 加载 config.local.py 失败，回退到环境变量/默认值: {_e}")
    _local_config = None


def _local(name, default=None):
    """从 config.local.py 读取顶层变量；不存在则返回 default。"""
    return getattr(_local_config, name, default) if _local_config is not None else default


# 邮件配置
# 优先从本地配置文件读取
_local_email_config = _local("EMAIL_CONFIG", {}) or {}

EMAIL_CONFIG = {
    "recipient": "1276949607@qq.com",
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "sender_email": _local_email_config.get("sender_email") or os.environ.get("EMAIL_SENDER", ""),  # 优先从config.local.py读取
    "sender_password": _local_email_config.get("sender_password") or os.environ.get("EMAIL_PASSWORD", ""),  # 优先从config.local.py读取
    "mode": "digest",  # 邮件模式: "full" 完整版（含摘要）, "digest" 摘要版（仅标题列表）
}

# 微信推送配置（Server酱）
# 优先从本地配置文件读取
_local_wechat_config = _local("WECHAT_CONFIG", {}) or {}

WECHAT_CONFIG = {
    "enabled": _local_wechat_config.get("enabled", False),  # 是否启用微信推送
    "sendkey": _local_wechat_config.get("sendkey") or os.environ.get("SERVERCHAN_KEY", ""),  # Server酱SendKey，优先从config.local.py读取
}

# AI摘要配置
# 优先从本地配置文件读取，然后从环境变量读取
_local_ai_config = _local("AI_CONFIG", {}) or {}

AI_CONFIG = {
    "enabled": True,
    # provider 可选: aigw（默认，OpenAI-compatible gateway）、kimi、gemini、openrouter
    # Fallback / 回退 Kimi 配置: 将下行改为 "kimi" 即可切回
    # "provider": _local_ai_config.get("provider") or os.environ.get("AI_PROVIDER", "kimi"),
    "provider": _local_ai_config.get("provider") or os.environ.get("AI_PROVIDER", "aigw"),
    # API key：优先 AI_API_KEY，其次 KIMI_API_KEY，再其次 GEMINI_API_KEY（运行时注入，不可硬编码）
    "api_key": (
        _local_ai_config.get("api_key")
        or os.environ.get("AI_API_KEY")
        or os.environ.get("KIMI_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or ""
    ),
    # model：aigw 默认 gpt-5.5
    # Fallback / 回退 Kimi 配置: "kimi-k2-turbo-preview"
    # "model": _local_ai_config.get("model") or os.environ.get("AI_MODEL", "kimi-k2-turbo-preview"),
    "model": _local_ai_config.get("model") or os.environ.get("AI_MODEL", "gpt-5.5"),
    # base_url：aigw gateway；切回 Kimi 时可删除此行（Kimi 用 KIMI_BASE_URL）
    # Fallback / 回退: "https://supercodex.space/v1"
    "base_url": _local_ai_config.get("base_url") or os.environ.get("AI_BASE_URL") or os.environ.get("OPENROUTER_BASE_URL", "https://aigw.sotatts.online/v1"),
}

# 去重配置
DEDUP_CONFIG = {
    "enabled": True,  # 是否启用去重
    "similarity_threshold": 0.98,  # 标题相似度阈值（0-1）
}

# GitHub配置
GITHUB_CONFIG = {
    "repo_name": "literature-tracker",
    "branch": "main",
    "pages_branch": "gh-pages",
}

# 数据文件路径
DATA_DIR = "data"
ARTICLES_DIR = "articles"
HISTORY_FILE = "data/history.json"
FAVORITES_FILE = "data/favorites.json"


# 核心关注（ML × ferro/凝聚态）开关与阈值
CORE_FOCUS_CONFIG = {
    "enabled": (os.environ.get("CORE_FOCUS_ENABLED", "1").strip().lower() not in ("0", "false", "no")),
    "daily_max_items": int(os.environ.get("CORE_FOCUS_DAILY_MAX", "8")),
    "weekly_max_items": int(os.environ.get("CORE_FOCUS_WEEKLY_MAX", "20")),
    "min_score": float(os.environ.get("CORE_FOCUS_MIN_SCORE", "0.60")),
}

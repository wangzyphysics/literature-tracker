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
    "http://feeds.feedburner.com/acs/jacsat",
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
    "http://feeds.feedburner.com/acs/nalefd",
    "http://feeds.feedburner.com/acs/achre4",
    "http://feeds.feedburner.com/physicstodaynews",
    "https://iopscience.iop.org/journal/rss/2632-2153",
    "https://onlinelibrary.wiley.com/action/showFeed?jc=15214095&type=etoc&feed=rss",
    "https://onlinelibrary.wiley.com/action/showFeed?jc=16163028&type=etoc&feed=rss",
    "https://onlinelibrary.wiley.com/action/showFeed?jc=21983844&type=etoc&feed=rss",
    "https://rss.arxiv.org/rss/cond-mat",
    "https://rss.arxiv.org/rss/physics",
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
]

# 关键词列表（用于筛选文献）
KEYWORDS = [
    "ferro",
    "machine",
    "learn",
    "magne",
    "neural",
    "network",
    "potential",
    "hamiltonian",
]

import os

# 邮件配置
EMAIL_CONFIG = {
    "recipient": "594836947@qq.com",
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "sender_email": os.environ.get("EMAIL_SENDER", ""),  # 从环境变量或手动配置
    "sender_password": os.environ.get("EMAIL_PASSWORD", ""),  # 从环境变量或手动配置
    "mode": "digest",  # 邮件模式: "full" 完整版（含摘要）, "digest" 摘要版（仅标题列表）
}

# 微信推送配置（Server酱）
WECHAT_CONFIG = {
    "enabled": False,  # 是否启用微信推送
    "sendkey": os.environ.get("SERVERCHAN_KEY", ""),  # Server酱SendKey，从 https://sct.ftqq.com/ 获取
}

# 去重配置
DEDUP_CONFIG = {
    "enabled": True,  # 是否启用去重
    "similarity_threshold": 0.9,  # 标题相似度阈值（0-1）
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

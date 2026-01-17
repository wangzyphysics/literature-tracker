#!/usr/bin/env python3
"""
周报生成器 - 每周总结Nature/Science系列的磁性/铁电工作
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ai_summarizer import GeminiProvider

try:
    from config import AI_CONFIG as DEFAULT_AI_CONFIG
except ImportError:
    DEFAULT_AI_CONFIG = {}


class WeeklySummarizer:
    """周报生成器"""
    
    # 顶刊列表 - 精确匹配，避免误匹配
    TOP_JOURNALS = [
        # Nature 系列
        'Nature',
        'Nature Materials',
        'Nature Physics',
        'Nature Chemistry',
        'Nature Communications',
        'Nature Nanotechnology',
        'Nature Electronics',
        'Nature Energy',
        'Nat. Mater.',
        'Nat. Phys.',
        'Nat. Chem.',
        'Nat. Commun.',
        'Nat. Nanotechnol.',
        'Nat. Electron.',
        'Nat. Energy',
        # Science 系列（注意：只包含正刊，不包含 ScienceDirect）
        'Science',
        'Science Advances',
        'Sci. Adv.',
        # 其他顶刊
        'Physical Review Letters',
        'Phys. Rev. Lett.',
        'PRL',
        'Advanced Materials',
        'Adv. Mater.'
    ]
    
    # 磁性/铁电关键词
    KEYWORDS = [
        'ferroelectric', 'ferromagnet', 'multiferroic', 'piezoelectric',
        'antiferroelectric', 'antiferromagnet', 'magnetoelectric',
        'polarization', 'magnetization', 'domain wall', 'skyrmion',
        'spin', 'magnetic', 'ferroic', 'perovskite',
        '铁电', '铁磁', '多铁', '压电', '反铁电', '反铁磁', '磁电',
        '极化', '磁化', '畴壁', '斯格明子', '自旋', '磁性', '铁性'
    ]
    
    def __init__(self, api_key: str = None):
        """初始化周报生成器"""
        if not api_key:
            api_key = os.environ.get('AI_API_KEY', '') or DEFAULT_AI_CONFIG.get('api_key', '')
        
        if api_key:
            self.provider = GeminiProvider(api_key)
        else:
            self.provider = None
            print("⚠️ 未配置AI API密钥，将使用基础模板")
    
    def filter_articles(self, articles: List[Dict], start_date: str, end_date: str) -> List[Dict]:
        """筛选符合条件的文献"""
        filtered = []
        
        # 排除关键词（这些不是真正的期刊）
        EXCLUDE_KEYWORDS = [
            'sciencedirect', 'springer', 'table of contents', 'toc',
            'editor', 'suggestion', 'news', 'highlight'
        ]
        
        for article in articles:
            # 检查日期范围
            pub_date = article.get('pub_date', '')
            if not (start_date <= pub_date <= end_date):
                continue
            
            # 检查期刊 - 精确匹配，避免误匹配
            journal = article.get('journal', '')
            if not journal:
                continue
            
            journal_lower = journal.lower()
            
            # 排除非期刊内容
            if any(exclude in journal_lower for exclude in EXCLUDE_KEYWORDS):
                continue
            
            # 精确匹配顶刊列表
            is_top_journal = False
            for top_journal in self.TOP_JOURNALS:
                top_lower = top_journal.lower()
                
                # 精确匹配
                if journal == top_journal:
                    is_top_journal = True
                    break
                
                # 包含匹配（但要小心处理）
                if top_lower in journal_lower:
                    # 特殊处理 Science：必须是 "Science" 或 "Science Advances"，不能是 "ScienceDirect"
                    if top_lower == 'science':
                        if journal_lower == 'science' or journal_lower.startswith('science advances') or journal_lower.startswith('sci. adv'):
                            is_top_journal = True
                            break
                        else:
                            continue
                    else:
                        is_top_journal = True
                        break
            
            if not is_top_journal:
                continue
            
            # 检查关键词
            text = ' '.join([
                article.get('title', ''),
                article.get('title_zh', ''),
                article.get('abstract', ''),
                article.get('abstract_zh', '')
            ]).lower()
            
            if any(keyword.lower() in text for keyword in self.KEYWORDS):
                filtered.append(article)
        
        return filtered
    
    def generate_weekly_summary(self, articles: List[Dict], week_start: str) -> Dict:
        """生成周报"""
        # 计算周结束日期
        start_date = datetime.strptime(week_start, '%Y-%m-%d')
        end_date = start_date + timedelta(days=6)
        week_end = end_date.strftime('%Y-%m-%d')
        
        # 筛选文献
        filtered_articles = self.filter_articles(articles, week_start, week_end)
        
        if not filtered_articles:
            return self._empty_summary(week_start, week_end)
        
        # 按期刊分组
        by_journal = {}
        for article in filtered_articles:
            journal = article.get('journal', '其他')
            if journal not in by_journal:
                by_journal[journal] = []
            by_journal[journal].append(article)
        
        # 使用AI生成总结
        if self.provider:
            try:
                summary = self._generate_ai_summary(filtered_articles, week_start, week_end, by_journal)
                return summary
            except Exception as e:
                print(f"❌ AI生成失败: {e}")
                return self._fallback_summary(filtered_articles, week_start, week_end, by_journal)
        else:
            return self._fallback_summary(filtered_articles, week_start, week_end, by_journal)
    
    def _generate_ai_summary(self, articles: List[Dict], week_start: str, week_end: str, by_journal: Dict) -> Dict:
        """使用AI生成周报"""
        
        # 构建提示词
        articles_text = []
        for i, article in enumerate(articles, 1):
            title = article.get('title_zh') or article.get('title', '')
            journal = article.get('journal', '')
            link = article.get('link', '')
            abstract = (article.get('abstract_zh') or article.get('abstract', ''))[:400]
            
            articles_text.append(f"""
{i}. 【{journal}】{title}
   链接: {link}
   摘要: {abstract}...
""")
        
        articles_str = '\n'.join(articles_text)
        
        prompt = f"""你是一位专业的凝聚态物理/材料科学研究助手。请分析以下{week_start}至{week_end}这一周内，Nature/Science系列期刊发表的{len(articles)}篇磁性/铁电相关文献，生成一份专业的周报。

文献列表:
{articles_str}

请按以下格式输出（使用JSON格式）:
{{
    "overview": "本周总览：文献总数、主要研究方向、重要发现（3-4句话）",
    "highlights": [
        {{
            "title": "文献标题",
            "journal": "期刊名",
            "link": "原文链接",
            "material": "研究材料体系（如BaTiO3、BiFeO3等）",
            "property": "研究性质（如铁电性、磁性、多铁性等）",
            "method": "研究方法（如第一性原理、实验、机器学习等）",
            "innovation": "核心创新点（50字以内）",
            "significance": "研究意义（30字以内）"
        }}
    ],
    "by_topic": {{
        "铁电材料": ["文献链接1", "文献链接2"],
        "磁性材料": ["文献链接1", "文献链接2"],
        "多铁性材料": ["文献链接1", "文献链接2"],
        "方法学创新": ["文献链接1", "文献链接2"]
    }},
    "trends": "本周研究趋势和热点分析（4-5句话）",
    "outlook": "未来研究方向展望（2-3句话）"
}}

要求:
1. highlights选择5-8篇最重要的文献，优先选择Nature/Science正刊
2. innovation要突出与以往研究的不同之处
3. 使用专业术语，但保持可读性
4. 确保所有链接都是原始文献链接
5. 使用中文输出"""
        
        response = self.provider.call_api(prompt)
        
        # 解析响应
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError("无法解析JSON")
        
        return {
            'week_start': week_start,
            'week_end': week_end,
            'total': len(articles),
            'overview': data.get('overview', ''),
            'highlights': data.get('highlights', []),
            'by_topic': data.get('by_topic', {}),
            'by_journal': by_journal,
            'trends': data.get('trends', ''),
            'outlook': data.get('outlook', ''),
            'articles': articles,
            'generated_by': 'gemini'
        }
    
    def _fallback_summary(self, articles: List[Dict], week_start: str, week_end: str, by_journal: Dict) -> Dict:
        """降级周报（无AI）"""
        
        # 按期刊排序，Nature/Science正刊优先
        sorted_articles = sorted(articles, key=lambda a: (
            0 if a.get('journal') == 'Nature' else
            1 if a.get('journal') == 'Science' else
            2 if 'Nature' in a.get('journal', '') else
            3 if 'Science' in a.get('journal', '') else 4
        ))
        
        # 生成亮点
        highlights = []
        for article in sorted_articles[:8]:
            highlights.append({
                'title': article.get('title_zh') or article.get('title', ''),
                'journal': article.get('journal', ''),
                'link': article.get('link', ''),
                'material': '待分析',
                'property': '磁性/铁电',
                'method': '待分析',
                'innovation': (article.get('abstract_zh') or article.get('abstract', ''))[:100] + '...',
                'significance': '顶刊发表'
            })
        
        # 统计期刊分布
        journal_stats = {j: len(arts) for j, arts in by_journal.items()}
        journal_list = ', '.join([f"{j}({n}篇)" for j, n in sorted(journal_stats.items(), key=lambda x: -x[1])[:5]])
        
        return {
            'week_start': week_start,
            'week_end': week_end,
            'total': len(articles),
            'overview': f"本周({week_start}至{week_end})共收录{len(articles)}篇磁性/铁电相关文献，主要发表在{journal_list}。",
            'highlights': highlights,
            'by_topic': {},
            'by_journal': by_journal,
            'trends': '（AI分析暂不可用）',
            'outlook': '（AI分析暂不可用）',
            'articles': articles,
            'generated_by': 'fallback'
        }
    
    def _empty_summary(self, week_start: str, week_end: str) -> Dict:
        """空周报"""
        return {
            'week_start': week_start,
            'week_end': week_end,
            'total': 0,
            'overview': f"本周({week_start}至{week_end})暂无符合条件的文献。",
            'highlights': [],
            'by_topic': {},
            'by_journal': {},
            'trends': '',
            'outlook': '',
            'articles': [],
            'generated_by': 'empty'
        }
    
    def save_summary_html(self, summary: Dict, output_dir: str = 'docs/weekly') -> str:
        """保存周报为HTML"""
        week_start = summary['week_start']
        week_end = summary['week_end']
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, f"{week_start}.html")
        
        # 生成亮点HTML
        highlights_html = ''
        for h in summary.get('highlights', []):
            highlights_html += f'''
            <div class="highlight-card">
                <h4><a href="{h.get('link', '#')}" target="_blank">{h.get('title', '')}</a></h4>
                <div class="highlight-meta">
                    <span class="journal-tag">{h.get('journal', '')}</span>
                    <span class="property-tag">{h.get('property', '')}</span>
                </div>
                <div class="highlight-details">
                    <div><strong>材料体系:</strong> {h.get('material', '')}</div>
                    <div><strong>研究方法:</strong> {h.get('method', '')}</div>
                </div>
                <p class="highlight-innovation"><strong>创新点:</strong> {h.get('innovation', '')}</p>
                <p class="highlight-significance"><strong>意义:</strong> {h.get('significance', '')}</p>
            </div>
            '''
        
        # 生成期刊统计HTML
        journal_stats_html = ''
        by_journal = summary.get('by_journal', {})
        for journal, arts in sorted(by_journal.items(), key=lambda x: -len(x[1])):
            journal_stats_html += f'''
            <div class="journal-stat">
                <div class="journal-name">{journal}</div>
                <div class="journal-count">{len(arts)} 篇</div>
            </div>
            '''
        
        # 生成完整HTML
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>周报 - {week_start} 至 {week_end}</title>
    <link rel="stylesheet" href="../style.css">
    <style>
        .weekly-container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }}
        .weekly-header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            color: white;
        }}
        .weekly-header h1 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .weekly-header .date-range {{
            font-size: 1.2em;
            opacity: 0.95;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: var(--bg-card);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            box-shadow: var(--shadow-md);
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: var(--accent-primary);
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: var(--text-muted);
            font-size: 0.9em;
        }}
        .section {{
            background: var(--bg-card);
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 25px;
            box-shadow: var(--shadow-md);
        }}
        .section h2 {{
            margin: 0 0 20px 0;
            color: var(--text-primary);
            border-bottom: 2px solid var(--accent-primary);
            padding-bottom: 10px;
        }}
        .highlight-card {{
            border-left: 4px solid var(--accent-primary);
            padding: 20px;
            margin-bottom: 20px;
            background: var(--bg-primary);
            border-radius: 0 8px 8px 0;
        }}
        .highlight-card h4 {{
            margin: 0 0 12px 0;
            font-size: 1.1em;
        }}
        .highlight-card h4 a {{
            color: var(--text-primary);
            text-decoration: none;
        }}
        .highlight-card h4 a:hover {{
            color: var(--accent-primary);
        }}
        .highlight-meta {{
            display: flex;
            gap: 10px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }}
        .journal-tag {{
            background: var(--accent-primary);
            color: white;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 0.85em;
            font-weight: 500;
        }}
        .property-tag {{
            background: var(--color-ai-tag);
            color: white;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 0.85em;
        }}
        .highlight-details {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 12px;
            font-size: 0.9em;
            color: var(--text-secondary);
        }}
        .highlight-innovation {{
            color: var(--text-secondary);
            margin: 10px 0;
            line-height: 1.6;
        }}
        .highlight-significance {{
            color: var(--color-ai-tag);
            font-size: 0.9em;
            margin: 8px 0 0 0;
        }}
        .journal-stat {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            margin-bottom: 8px;
            background: var(--bg-primary);
            border-radius: 8px;
        }}
        .journal-name {{
            font-weight: 500;
            color: var(--text-primary);
        }}
        .journal-count {{
            background: var(--accent-primary);
            color: white;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 0.9em;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: var(--accent-primary);
            text-decoration: none;
            font-weight: 500;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
        .generated-by {{
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85em;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
        }}
        
        @media (max-width: 767px) {{
            .highlight-details {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="weekly-container">
        <a href="../index.html" class="back-link">← 返回主页</a>
        
        <div class="weekly-header">
            <h1>🔬 磁性/铁电周报</h1>
            <div class="date-range">{week_start} 至 {week_end}</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{summary.get('total', 0)}</div>
                <div class="stat-label">本周文献</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(summary.get('highlights', []))}</div>
                <div class="stat-label">重点推荐</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(by_journal)}</div>
                <div class="stat-label">涉及期刊</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 本周总览</h2>
            <p>{summary.get('overview', '')}</p>
        </div>
        
        {f'<div class="section"><h2>⭐ 重点文献</h2>{highlights_html}</div>' if highlights_html else ''}
        
        {f'<div class="section"><h2>🔥 研究趋势</h2><p>{summary.get("trends", "")}</p></div>' if summary.get('trends') else ''}
        
        {f'<div class="section"><h2>🔮 未来展望</h2><p>{summary.get("outlook", "")}</p></div>' if summary.get('outlook') else ''}
        
        {f'<div class="section"><h2>📚 期刊分布</h2>{journal_stats_html}</div>' if journal_stats_html else ''}
        
        <div class="generated-by">
            由 {summary.get('generated_by', 'AI')} 生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
    </div>
    
    <script>
        // 主题支持
        const theme = localStorage.getItem('literature_theme') || 'light';
        document.documentElement.setAttribute('data-theme', theme);
    </script>
</body>
</html>'''
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ 周报已保存: {filepath}")
        
        # 更新周报索引
        self._update_weekly_index(week_start)
        
        return filepath
    
    def _update_weekly_index(self, week_start: str):
        """更新周报索引"""
        import glob
        
        weekly_dir = 'docs/weekly'
        index_file = os.path.join(weekly_dir, 'index.json')
        
        # 扫描所有周报文件
        weekly_files = glob.glob(os.path.join(weekly_dir, '????-??-??.html'))
        weeklies = []
        
        for f in sorted(weekly_files, reverse=True):
            filename = os.path.basename(f)
            date_str = filename.replace('.html', '')
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                end_date = date_obj + timedelta(days=6)
                weeklies.append({
                    'week_start': date_str,
                    'week_end': end_date.strftime('%Y-%m-%d'),
                    'file': filename
                })
            except ValueError:
                continue
        
        # 保存索引
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump({'weeklies': weeklies, 'updated': datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 周报索引已更新: {len(weeklies)} 个周报")


def generate_weekly_summary(week_start: str = None, api_key: str = None) -> Optional[str]:
    """
    便捷函数：生成周报
    
    Args:
        week_start: 周开始日期 (YYYY-MM-DD)，默认为本周一
        api_key: API密钥
        
    Returns:
        输出文件路径
    """
    # 加载文献数据
    try:
        with open('docs/data/index.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        articles = data.get('articles', [])
    except FileNotFoundError:
        print("❌ 未找到数据文件")
        return None
    
    # 确定周开始日期
    if not week_start:
        today = datetime.now()
        # 计算本周一
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        week_start = monday.strftime('%Y-%m-%d')
    
    # 生成周报
    summarizer = WeeklySummarizer(api_key)
    summary = summarizer.generate_weekly_summary(articles, week_start)
    
    if summary['total'] == 0:
        print(f"📭 {week_start} 这周没有符合条件的文献")
        return None
    
    return summarizer.save_summary_html(summary)


if __name__ == '__main__':
    import sys
    
    # 使用命令行参数
    week_start = sys.argv[1] if len(sys.argv) > 1 else None
    generate_weekly_summary(week_start)

#!/usr/bin/env python3
"""周报相关 prompt 构造(stdlib-only,不依赖任何第三方库)。"""


def _build_analyze_prompt(title: str, journal: str, abstract: str) -> str:
    """单篇详细解读 prompt:一段 2~3 句、≤100 字的中文分析。"""
    return f"""请对以下文献进行分析，生成一段 2~3 句、≤100 字的中文解读，突出核心创新点、最强结论与研究意义。

标题: {title}
期刊: {journal}
摘要: {abstract[:500]}

要求:
1. 用中文输出
2. 2~3 句、≤100 字
3. 突出核心创新点与最强结论
4. 说明研究意义或应用价值
5. 不要照抄摘要，而是分析总结

直接输出分析结果，不要添加任何前缀或格式："""

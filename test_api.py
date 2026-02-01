#!/usr/bin/env python3
"""
测试 AI API 调用：使用 config / config.local 中的 AI_CONFIG，请求 OpenRouter/Gemini 等并打印结果。
用法: python test_api.py
"""
import sys
import os

# 确保从项目根加载
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.realpath(__file__))))

def main():
    print("=" * 50)
    print("AI API 调用测试")
    print("=" * 50)

    # 1. 加载配置
    try:
        from config import AI_CONFIG
    except ImportError as e:
        print("[FAIL] 无法导入 config:", e)
        return 1

    provider = AI_CONFIG.get("provider") or "gemini"
    api_key = (AI_CONFIG.get("api_key") or "").strip()
    model = AI_CONFIG.get("model") or "z-ai/glm-4.5-air:free"

    print("\n1. 配置")
    print("   provider:", provider)
    print("   api_key:  len=%d, 前8位=%s" % (len(api_key), (api_key[:8] + "...") if len(api_key) >= 8 else "(空)"))
    print("   model:   ", model)

    if not api_key:
        print("\n[FAIL] api_key 为空，请在 config.local.py 的 AI_CONFIG 中配置 api_key，或设置环境变量 AI_API_KEY")
        return 1

    # 2. 调用 API（通过 ai_summarizer 的 AISummarizer，与日报/周报同一路径）
    try:
        from ai_summarizer import AISummarizer
    except ImportError as e:
        print("[FAIL] 无法导入 ai_summarizer:", e)
        return 1

    print("\n2. 初始化 AISummarizer 并调用 API...")
    try:
        summarizer = AISummarizer(provider, api_key)
        reply = summarizer.provider.call_api("请用一句话回答：1+1等于几？")
        print("   状态: 成功")
        print("   回复: ", reply.strip()[:200] + ("..." if len(reply) > 200 else ""))
    except Exception as e:
        print("   状态: [FAIL]")
        print("   错误: ", type(e).__name__, str(e))
        return 1

    print("\n" + "=" * 50)
    print("[OK] 测试通过")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())

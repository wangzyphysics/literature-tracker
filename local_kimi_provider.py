#!/usr/bin/env python3
"""
本地Kimi Provider - 直接利用当前AI助手的能力生成摘要
通过文件接口实现与主系统的通信
"""

import os
import json
import time
from typing import Optional
from ai_summarizer import AIProvider

class LocalKimiProvider(AIProvider):
    """
    本地Kimi Provider - 不调用远程API，而是通过文件接口
    让OpenClaw AI助手直接生成内容
    """
    
    def __init__(self, model: str = "kimi-k2.5"):
        self.model = model
        self.request_dir = "/tmp/literature-tracker/ai_requests"
        self.response_dir = "/tmp/literature-tracker/ai_responses"
        os.makedirs(self.request_dir, exist_ok=True)
        os.makedirs(self.response_dir, exist_ok=True)
    
    def call_api(self, prompt: str) -> str:
        """
        将请求写入文件，然后等待响应
        这是第一阶段：系统准备请求
        """
        # 生成唯一请求ID
        request_id = f"{int(time.time() * 1000)}"
        
        # 保存请求
        request_file = os.path.join(self.request_dir, f"{request_id}.json")
        with open(request_file, "w", encoding="utf-8") as f:
            json.dump({
                "id": request_id,
                "prompt": prompt,
                "timestamp": time.time()
            }, f, ensure_ascii=False, indent=2)
        
        print(f"📝 AI请求已保存: {request_file}")
        print(f"⏳ 等待AI生成响应... (需要手动触发AI处理)")
        
        # 检查是否有预生成的响应（用于自动化）
        response_file = os.path.join(self.response_dir, f"{request_id}.json")
        
        # 如果响应已存在（预先准备好的），直接返回
        if os.path.exists(response_file):
            with open(response_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"✅ 找到预生成响应: {response_file}")
            return data.get("content", "")
        
        # 否则，尝试读取最新的通用响应文件
        # 这是给cron任务用的：AI助手会生成一个daily_response.json
        daily_response = os.path.join(self.response_dir, "daily_response.json")
        if os.path.exists(daily_response):
            with open(daily_response, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 检查是否是今天的
            if data.get("date") == self._today():
                print(f"✅ 使用今日预生成摘要")
                return data.get("content", "")
        
        # 如果没有预生成内容，返回一个基础结构
        # 让系统可以继续运行（降级模式）
        print("⚠️ 未找到AI响应，使用基础模板")
        return self._fallback_response()
    
    def _today(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")
    
    def _fallback_response(self) -> str:
        """当AI不可用时返回的基础JSON模板"""
        return json.dumps({
            "overview": "今日文献已收录，AI摘要待生成。",
            "trends": "",
            "full_list": [],
            "ml_highlights": [],
            "ferro_highlights": []
        }, ensure_ascii=False)


# 工厂函数扩展
def build_provider_extended(api_provider: str, api_key: str, model: str = None):
    """扩展的Provider工厂，支持localkimi模式"""
    name = (api_provider or "").strip().lower()
    if name in ("localkimi", "local-kimi", "lk"):
        return LocalKimiProvider(model=model)
    # 否则使用原工厂
    from ai_summarizer import build_provider
    return build_provider(api_provider, api_key, model)

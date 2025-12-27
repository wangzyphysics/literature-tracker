"""
微信通知模块 - 通过Server酱发送微信推送
"""

import requests
from typing import List, Optional, Tuple


class WeChatNotifier:
    """微信通知器 - 使用Server酱"""
    
    def __init__(self, sendkey: str):
        """
        初始化微信通知器
        
        Args:
            sendkey: Server酱的SendKey
        """
        self.sendkey = sendkey
        self.api_url = f"https://sctapi.ftqq.com/{sendkey}.send"
    
    def validate_config(self) -> Tuple[bool, str]:
        """
        验证配置完整性
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not self.sendkey:
            return False, "Server酱SendKey未配置"
        
        if len(self.sendkey) < 10:
            return False, "Server酱SendKey格式无效"
        
        return True, ""
    
    def send_notification(self, articles: List, title: Optional[str] = None) -> bool:
        """
        发送新文献通知
        
        Args:
            articles: 文献列表
            title: 自定义标题（可选）
            
        Returns:
            bool: 是否发送成功
        """
        if not articles:
            print("没有新文献，跳过微信推送")
            return True
        
        # 验证配置
        is_valid, error_msg = self.validate_config()
        if not is_valid:
            print(f"⚠️ 微信推送跳过: {error_msg}")
            return False
        
        try:
            # 生成消息内容
            msg_title = title or f"📚 文献更新：{len(articles)}篇新文献"
            msg_content = self._generate_content(articles)
            
            # 发送请求
            data = {
                "title": msg_title,
                "desp": msg_content,
                "channel": "9"  # 默认推送渠道
            }
            
            response = requests.post(self.api_url, data=data, timeout=30)
            result = response.json()
            
            if result.get("code") == 0:
                print(f"✅ 微信推送成功: {len(articles)}篇文献通知已发送")
                return True
            else:
                error = result.get("message", "未知错误")
                print(f"❌ 微信推送失败: {error}")
                return False
                
        except requests.exceptions.Timeout:
            print("❌ 微信推送失败: 请求超时")
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ 微信推送失败: 网络错误 - {e}")
            return False
        except Exception as e:
            print(f"❌ 微信推送失败: {type(e).__name__} - {e}")
            return False
    
    def _generate_content(self, articles: List) -> str:
        """
        生成Markdown格式的消息内容
        
        Args:
            articles: 文献列表
            
        Returns:
            str: Markdown格式内容
        """
        # 统计AI相关文献
        ai_keywords = ['machine', 'learn', 'neural', 'network']
        ai_count = 0
        for article in articles:
            text = f"{article.title} {getattr(article, 'abstract', '')}".lower()
            if any(kw in text for kw in ai_keywords):
                ai_count += 1
        
        non_ai_count = len(articles) - ai_count
        
        # 生成内容
        content = f"## 📊 统计\n\n"
        content += f"- 总计: **{len(articles)}** 篇\n"
        content += f"- 🤖 AI相关: **{ai_count}** 篇\n"
        content += f"- 📚 非AI: **{non_ai_count}** 篇\n\n"
        content += "---\n\n"
        content += "## 📖 文献列表\n\n"
        
        # 按期刊分组
        by_journal = {}
        for article in articles:
            journal = getattr(article, 'journal', '未知期刊') or '未知期刊'
            if journal not in by_journal:
                by_journal[journal] = []
            by_journal[journal].append(article)
        
        for journal, journal_articles in by_journal.items():
            content += f"### 📰 {journal}\n\n"
            
            for article in journal_articles:
                title_zh = getattr(article, 'title_zh', '') or article.title
                link = getattr(article, 'link', '')
                pub_date = getattr(article, 'pub_date', '')
                
                # 判断是否AI相关
                text = f"{article.title} {getattr(article, 'abstract', '')}".lower()
                is_ai = any(kw in text for kw in ai_keywords)
                ai_tag = "🤖" if is_ai else "📚"
                
                content += f"- {ai_tag} **{title_zh}**\n"
                if pub_date:
                    content += f"  - 📅 {pub_date}\n"
                if link:
                    content += f"  - 🔗 [查看原文]({link})\n"
                content += "\n"
        
        content += "---\n\n"
        content += "*此消息由文献追踪系统自动发送*"
        
        return content
    
    def test_connection(self) -> bool:
        """
        测试Server酱连接
        
        Returns:
            bool: 连接是否正常
        """
        is_valid, error_msg = self.validate_config()
        if not is_valid:
            print(f"❌ 配置无效: {error_msg}")
            return False
        
        try:
            data = {
                "title": "🔔 文献追踪系统测试",
                "desp": "如果您收到此消息，说明微信推送配置成功！"
            }
            
            response = requests.post(self.api_url, data=data, timeout=30)
            result = response.json()
            
            if result.get("code") == 0:
                print("✅ Server酱连接测试成功")
                return True
            else:
                print(f"❌ Server酱连接测试失败: {result.get('message', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"❌ Server酱连接测试失败: {e}")
            return False

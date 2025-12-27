"""
邮件通知模块 - 发送新文献通知
增强版：完善的错误处理和配置验证
"""

import smtplib
import socket
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Tuple, Optional


class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self, smtp_server: str, smtp_port: int, 
                 sender_email: str, sender_password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
    
    def validate_config(self) -> Tuple[bool, str]:
        """
        验证邮件配置完整性
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        errors = []
        
        if not self.smtp_server:
            errors.append("SMTP服务器地址未配置")
        
        if not self.smtp_port:
            errors.append("SMTP端口未配置")
        elif not isinstance(self.smtp_port, int) or self.smtp_port <= 0:
            errors.append(f"SMTP端口无效: {self.smtp_port}")
        
        if not self.sender_email:
            errors.append("发件人邮箱未配置")
        elif '@' not in self.sender_email:
            errors.append(f"发件人邮箱格式无效: {self.sender_email}")
        
        if not self.sender_password:
            errors.append("发件人密码/授权码未配置")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, ""
    
    def send_notification(self, recipient: str, articles: list) -> bool:
        """
        发送新文献通知邮件
        
        Args:
            recipient: 收件人邮箱
            articles: 文献列表
            
        Returns:
            bool: 是否发送成功
        """
        if not articles:
            print("没有新文献，跳过邮件发送")
            return True
        
        # 验证配置
        is_valid, error_msg = self.validate_config()
        if not is_valid:
            print(f"❌ 邮件配置不完整: {error_msg}")
            print("   请检查环境变量 EMAIL_SENDER 和 EMAIL_PASSWORD 是否已设置")
            return False
        
        # 验证收件人
        if not recipient or '@' not in recipient:
            print(f"❌ 收件人邮箱无效: {recipient}")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📚 文献追踪更新 - {len(articles)}篇新文献 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
            msg['From'] = self.sender_email
            msg['To'] = recipient
            
            # 生成邮件内容
            html_content = self._generate_html(articles)
            text_content = self._generate_text(articles)
            
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 发送邮件 - 使用SSL连接
            print(f"   正在连接 {self.smtp_server}:{self.smtp_port}...")
            
            # 创建SSL上下文
            context = ssl.create_default_context()
            
            try:
                # 尝试SSL连接（端口465）
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context, timeout=30) as server:
                    print("   SSL连接成功，正在登录...")
                    server.login(self.sender_email, self.sender_password)
                    print("   登录成功，正在发送邮件...")
                    server.sendmail(self.sender_email, recipient, msg.as_string())
            except ssl.SSLError as e:
                # 如果SSL失败，尝试STARTTLS（端口587）
                print(f"   SSL连接失败，尝试STARTTLS...")
                with smtplib.SMTP(self.smtp_server, 587, timeout=30) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(self.sender_email, self.sender_password)
                    server.sendmail(self.sender_email, recipient, msg.as_string())
            
            print(f"✅ 邮件发送成功: {len(articles)}篇文献通知已发送到 {recipient}")
            return True
            
        except socket.timeout:
            print(f"❌ 邮件发送失败: 连接超时")
            print(f"   请检查网络连接和SMTP服务器地址: {self.smtp_server}:{self.smtp_port}")
            return False
            
        except socket.gaierror as e:
            print(f"❌ 邮件发送失败: 无法解析服务器地址")
            print(f"   服务器: {self.smtp_server}")
            print(f"   错误详情: {e}")
            return False
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ 邮件发送失败: 认证失败")
            print(f"   请检查邮箱地址和授权码是否正确")
            print(f"   注意: QQ邮箱需要使用授权码而非登录密码")
            print(f"   错误代码: {e.smtp_code}, 错误信息: {e.smtp_error}")
            return False
            
        except smtplib.SMTPRecipientsRefused as e:
            print(f"❌ 邮件发送失败: 收件人被拒绝")
            print(f"   收件人: {recipient}")
            print(f"   错误详情: {e}")
            return False
            
        except smtplib.SMTPSenderRefused as e:
            print(f"❌ 邮件发送失败: 发件人被拒绝")
            print(f"   发件人: {self.sender_email}")
            print(f"   错误详情: {e}")
            return False
            
        except smtplib.SMTPException as e:
            print(f"❌ 邮件发送失败: SMTP错误")
            print(f"   错误类型: {type(e).__name__}")
            print(f"   错误详情: {e}")
            return False
            
        except Exception as e:
            print(f"❌ 邮件发送失败: 未知错误")
            print(f"   错误类型: {type(e).__name__}")
            print(f"   错误详情: {e}")
            return False
    
    def _generate_html(self, articles: list) -> str:
        """生成HTML格式邮件内容"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .header h1 { margin: 0; font-size: 24px; }
        .header p { margin: 5px 0 0; opacity: 0.9; }
        .article { background: #f8f9fa; border-radius: 8px; padding: 15px; margin-bottom: 15px; border-left: 4px solid #667eea; }
        .article h2 { margin: 0 0 10px; font-size: 16px; color: #333; }
        .article h3 { margin: 5px 0; font-size: 14px; color: #666; font-weight: normal; }
        .meta { font-size: 12px; color: #888; margin-bottom: 10px; }
        .abstract { font-size: 13px; color: #555; margin-top: 10px; }
        .link { display: inline-block; margin-top: 10px; color: #667eea; text-decoration: none; font-size: 13px; }
        .link:hover { text-decoration: underline; }
        .footer { text-align: center; color: #888; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; }
        .ai-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-left: 8px; }
        .ai-tag.ai { background: #d1fae5; color: #059669; }
        .ai-tag.non-ai { background: #f3f4f6; color: #6b7280; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📚 文献追踪更新</h1>
        <p>发现 {count} 篇符合关键词的新文献</p>
    </div>
""".format(count=len(articles))
        
        for article in articles:
            authors = ", ".join(article.authors[:3]) if article.authors else "未知"
            if article.authors and len(article.authors) > 3:
                authors += " et al."
            
            abstract_zh = getattr(article, 'abstract_zh', '') or ''
            abstract_preview = abstract_zh[:300] + "..." if len(abstract_zh) > 300 else abstract_zh
            
            # 判断是否AI相关
            ai_keywords = ['machine', 'learn', 'neural', 'network']
            text = f"{article.title} {getattr(article, 'title_zh', '')} {getattr(article, 'abstract', '')} {abstract_zh}".lower()
            is_ai = any(kw in text for kw in ai_keywords)
            ai_tag = '<span class="ai-tag ai">🤖 AI</span>' if is_ai else '<span class="ai-tag non-ai">📚 非AI</span>'
            
            html += f"""
    <div class="article">
        <h2>{article.title} {ai_tag}</h2>
        <h3>{getattr(article, 'title_zh', '')}</h3>
        <div class="meta">
            <strong>{article.journal}</strong> | {article.pub_date} | {authors}
        </div>
        <div class="abstract">{abstract_preview}</div>
        <a href="{article.link}" class="link">查看原文 →</a>
    </div>
"""
        
        html += """
    <div class="footer">
        <p>此邮件由文献追踪系统自动发送</p>
    </div>
</body>
</html>
"""
        return html
    
    def _generate_text(self, articles: list) -> str:
        """生成纯文本格式邮件内容"""
        text = f"文献追踪更新 - 发现 {len(articles)} 篇新文献\n"
        text += "=" * 50 + "\n\n"
        
        for i, article in enumerate(articles, 1):
            authors = ", ".join(article.authors[:3]) if article.authors else "未知"
            title_zh = getattr(article, 'title_zh', '')
            
            text += f"{i}. {article.title}\n"
            if title_zh:
                text += f"   中文: {title_zh}\n"
            text += f"   期刊: {article.journal} | 日期: {article.pub_date}\n"
            text += f"   作者: {authors}\n"
            text += f"   链接: {article.link}\n\n"
        
        return text

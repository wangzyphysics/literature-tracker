# 本地配置文件说明

## 概述

为了保护敏感信息（如API密钥），系统支持使用本地配置文件 `config.local.py`。这个文件不会被提交到git仓库。

## 使用方法

1. **复制示例文件**：
   ```bash
   cp config.local.py.example config.local.py
   ```

2. **编辑配置文件**：
   打开 `config.local.py`，填入你的API密钥和其他配置：
   ```python
   # AI配置
   AI_CONFIG = {
       "provider": "openrouter",  # gemini, openrouter, siliconflow, groq, deepseek
       "api_key": "YOUR_API_KEY_HERE",  # 在这里填入你的API密钥
       "model": "stepfun/step-3.5-flash:free",  # OpenRouter 模型（provider=openrouter 时生效）
   }
   ```

3. **配置优先级**：
   - 第一优先级：`config.local.py` 中的配置
   - 第二优先级：环境变量（如 `AI_API_KEY`）
   - 第三优先级：`config.py` 中的默认值

## 支持的配置项

### AI配置 (AI_CONFIG)
- `provider`: AI服务提供商（"gemini", "openrouter", "siliconflow", "groq", "deepseek"）
- `api_key`: API密钥
- `model`: 模型名称（如 OpenRouter 的 `stepfun/step-3.5-flash:free`，或 Gemini 的 model id）

### 邮件配置 (EMAIL_CONFIG)
- `sender_email`: 发件人邮箱
- `sender_password`: 发件人密码

### 微信推送配置 (WECHAT_CONFIG)
- `enabled`: 是否启用微信推送（True/False）
- `sendkey`: Server酱SendKey

## 安全提示

- ✅ `config.local.py` 已在 `.gitignore` 中，不会被提交到git
- ✅ 不要将 `config.local.py` 文件分享给他人
- ✅ 如果使用git，确保 `config.local.py` 没有被意外提交

## 示例

完整的 `config.local.py` 示例：

```python
"""
本地配置文件
此文件不会被提交到git
"""

# AI配置
AI_CONFIG = {
    "provider": "openrouter",
    "api_key": "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "model": "stepfun/step-3.5-flash:free",
}

# 邮件配置（可选）
EMAIL_CONFIG = {
    "sender_email": "your_email@example.com",
    "sender_password": "your_app_password",
}

# 微信推送配置（可选）
WECHAT_CONFIG = {
    "enabled": True,
    "sendkey": "SCT1234567890abcdef",
}
```

#!/usr/bin/env python3
"""
生成最新两周的周报
"""

from datetime import datetime, timedelta
from weekly_summary import generate_weekly_summary
import time

# 计算最新两周的周一日期
today = datetime.now()
last_monday = today - timedelta(days=today.weekday())
week_before = last_monday - timedelta(days=7)

mondays = [week_before.strftime('%Y-%m-%d'), last_monday.strftime('%Y-%m-%d')]

print(f"📅 准备生成最新2周的周报")
print(f"日期: {mondays[0]} 和 {mondays[1]}\n")

for i, monday in enumerate(mondays, 1):
    print(f"[{i}/2] 生成 {monday} 周报...")
    
    try:
        result = generate_weekly_summary(monday)
        
        if result:
            print(f"✅ 成功生成: {result}\n")
        else:
            print(f"📭 该周无符合条件的文献\n")
        
        # 避免API速率限制
        if i < len(mondays):
            time.sleep(2)
            
    except Exception as e:
        print(f"❌ 生成失败: {e}\n")
        import traceback
        traceback.print_exc()
        continue

print("=" * 60)
print(f"📊 生成完成")
print("=" * 60)

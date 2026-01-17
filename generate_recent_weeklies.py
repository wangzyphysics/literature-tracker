#!/usr/bin/env python3
"""
批量生成最近两个月的周报
"""

from datetime import datetime, timedelta
from weekly_summary import generate_weekly_summary
import time

def generate_recent_weeklies(months=2):
    """生成最近N个月的周报"""
    
    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    # 找到起始周的周一
    days_since_monday = start_date.weekday()
    first_monday = start_date - timedelta(days=days_since_monday)
    
    # 生成所有周一日期
    mondays = []
    current = first_monday
    while current <= end_date:
        mondays.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=7)
    
    print(f"📅 准备生成 {len(mondays)} 周的周报")
    print(f"日期范围: {mondays[0]} 至 {mondays[-1]}\n")
    
    success_count = 0
    empty_count = 0
    error_count = 0
    
    for i, monday in enumerate(mondays, 1):
        print(f"[{i}/{len(mondays)}] 生成 {monday} 周报...")
        
        try:
            result = generate_weekly_summary(monday)
            
            if result:
                success_count += 1
                print(f"✅ 成功生成: {result}\n")
            else:
                empty_count += 1
                print(f"📭 该周无符合条件的文献\n")
            
            # 避免API速率限制，每次生成后等待
            if i < len(mondays):
                time.sleep(2)
                
        except Exception as e:
            error_count += 1
            print(f"❌ 生成失败: {e}\n")
            continue
    
    print("=" * 60)
    print(f"📊 生成完成统计:")
    print(f"  ✅ 成功: {success_count} 周")
    print(f"  📭 无文献: {empty_count} 周")
    print(f"  ❌ 失败: {error_count} 周")
    print(f"  📝 总计: {len(mondays)} 周")
    print("=" * 60)

if __name__ == '__main__':
    import sys
    
    # 支持命令行参数指定月数
    months = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    generate_recent_weeklies(months)

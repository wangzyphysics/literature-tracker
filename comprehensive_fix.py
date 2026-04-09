#!/usr/bin/env python3
"""
全面代码修复和严格测试
"""

import os
import sys
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def fix_bare_excepts():
    """修复所有裸 except 子句"""
    files_to_fix = [
        'abstract_scraper.py',
        'data_manager.py', 
        'weekly_summary.py'
    ]
    
    fixes = []
    for filename in files_to_fix:
        filepath = os.path.join(BASE_DIR, filename)
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        # 修复裸 except: -> except Exception:
        content = re.sub(r'except:\s*\n', 'except Exception:\n', content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            fixes.append(filename)
            print(f"✅ 修复 {filename} 中的裸 except 子句")
    
    return fixes

def verify_fixes():
    """验证修复"""
    print("\n🔍 验证修复...")
    
    # 检查是否还有裸 except
    bare_excepts = []
    for root, dirs, files in os.walk(BASE_DIR):
        # 跳过测试文件和隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if 'except:' in content and 'except Exception:' not in content.replace('except:', ''):
                        # 更精确的检查
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if re.match(r'^\s*except:\s*$', line):
                                bare_excepts.append(f"{file}:{i}")
                except:
                    pass
    
    if bare_excepts:
        print(f"⚠️ 仍有 {len(bare_excepts)} 处裸 except:")
        for loc in bare_excepts[:10]:
            print(f"   - {loc}")
    else:
        print("✅ 没有裸 except 子句")
    
    return len(bare_excepts) == 0

def run_import_tests():
    """运行导入测试"""
    print("\n📦 运行导入测试...")
    
    modules = [
        'ai_summarizer',
        'generate_daily_pages',
        'generate_with_local_ai',
        'prepare_ai_prompt',
        'weekly_summary',
        'abstract_scraper',
        'data_manager',
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except Exception as e:
            print(f"❌ {module}: {e}")
            failed.append(module)
    
    return failed

def run_functional_tests():
    """运行业务逻辑测试"""
    print("\n🧪 运行业务逻辑测试...")
    
    # 测试 ai_summarizer 的关键功能
    from ai_summarizer import AISummarizer
    
    summarizer = AISummarizer("gemini", "fake_key")
    
    # 测试 _summary_fields_missing
    assert summarizer._summary_fields_missing(None) == True
    assert summarizer._summary_fields_missing({}) == True
    assert summarizer._summary_fields_missing({"title_zh": "", "one_sentence_summary": ""}) == True
    assert summarizer._summary_fields_missing({"title_zh": "test", "one_sentence_summary": ""}) == True
    assert summarizer._summary_fields_missing({"title_zh": "", "one_sentence_summary": "test"}) == True
    assert summarizer._summary_fields_missing({"title_zh": "test", "one_sentence_summary": "test"}) == False
    print("✅ _summary_fields_missing 测试通过")
    
    # 测试 _load_json_lenient
    assert AISummarizer._load_json_lenient('{"key": "value"}')["key"] == "value"
    assert AISummarizer._load_json_lenient('```json\n{"key": "value"}\n```')["key"] == "value"
    print("✅ _load_json_lenient 测试通过")
    
    # 测试 fallback_summary
    fallback = summarizer.fallback_summary([], "2026-04-09")
    assert fallback["total"] == 0
    assert fallback["date"] == "2026-04-09"
    print("✅ fallback_summary 测试通过")
    
    # 测试 _build_missing_summaries_prompt 的边界检查
    articles = [{"title": "Article 1"}, {"title": "Article 2"}]
    prompt = summarizer._build_missing_summaries_prompt(articles, [1, 2, 5], "2026-04-09")
    assert "[1]" in prompt
    assert "[2]" in prompt
    assert "[5]" not in prompt  # 越界索引应该被跳过
    print("✅ _build_missing_summaries_prompt 边界检查测试通过")
    
    return True

def main():
    print("=" * 60)
    print("全面代码修复和严格测试")
    print("=" * 60)
    
    # 1. 修复裸 except
    fixed_files = fix_bare_excepts()
    print(f"\n📝 修复了 {len(fixed_files)} 个文件")
    
    # 2. 验证修复
    verify_ok = verify_fixes()
    
    # 3. 导入测试
    failed_modules = run_import_tests()
    
    # 4. 功能测试
    try:
        functional_ok = run_functional_tests()
    except Exception as e:
        print(f"❌ 功能测试失败: {e}")
        functional_ok = False
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"✅ 修复文件数: {len(fixed_files)}")
    print(f"{'✅' if verify_ok else '❌'} 裸 except 检查: {'通过' if verify_ok else '失败'}")
    print(f"{'✅' if not failed_modules else '❌'} 模块导入: {'通过' if not failed_modules else f'{len(failed_modules)} 个失败'}")
    print(f"{'✅' if functional_ok else '❌'} 功能测试: {'通过' if functional_ok else '失败'}")
    
    all_passed = verify_ok and not failed_modules and functional_ok
    
    if all_passed:
        print("\n🎉 所有测试通过！代码修复成功。")
    else:
        print("\n⚠️ 部分测试失败，请检查。")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

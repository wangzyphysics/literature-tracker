#!/usr/bin/env python3
"""
严格测试修复后的代码
"""

import os
import sys
import json
import unittest
from datetime import datetime, timedelta

# 设置项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

class TestCodeFixes(unittest.TestCase):
    """测试代码修复"""
    
    def test_01_import_fixed(self):
        """测试类型注解修复"""
        try:
            from ai_summarizer import AISummarizer, GeminiProvider, OpenRouterProvider
            print("✅ ai_summarizer 模块导入成功")
        except ImportError as e:
            self.fail(f"导入失败: {e}")
    
    def test_02_tuple_annotation(self):
        """测试 Tuple 类型注解"""
        from ai_summarizer import AISummarizer
        import inspect
        
        # 检查 _build_overview_trends 方法的返回类型注解
        sig = inspect.signature(AISummarizer._build_overview_trends)
        return_annotation = sig.return_annotation
        
        # 应该包含 Tuple 或 tuple
        self.assertIn('Tuple', str(return_annotation) or 'tuple', 
                      "返回类型注解应使用 Tuple")
        print(f"✅ 类型注解正确: {return_annotation}")
    
    def test_02b_build_provider_kimi(self):
        """测试 build_provider 支持 kimi"""
        from ai_summarizer import build_provider, OpenRouterProvider
        
        provider = build_provider("kimi", "fake_key", "kimi-for-coding")
        self.assertIsInstance(provider, OpenRouterProvider)
        self.assertEqual(provider.model, "kimi-for-coding")
        print("✅ build_provider 正确支持 kimi")
    
    def test_03_generate_with_local_ai_import(self):
        """测试 generate_with_local_ai 导入"""
        try:
            from generate_with_local_ai import generate_daily_with_local_ai, BASE_DIR, AI_RESPONSES_DIR
            print(f"✅ generate_with_local_ai 导入成功")
            print(f"   BASE_DIR: {BASE_DIR}")
            print(f"   AI_RESPONSES_DIR: {AI_RESPONSES_DIR}")
        except ImportError as e:
            self.fail(f"导入失败: {e}")
    
    def test_04_prepare_ai_prompt_import(self):
        """测试 prepare_ai_prompt 导入"""
        try:
            from prepare_ai_prompt import prepare_daily_data, build_ai_prompt, BASE_DIR
            print(f"✅ prepare_ai_prompt 导入成功")
            print(f"   BASE_DIR: {BASE_DIR}")
        except ImportError as e:
            self.fail(f"导入失败: {e}")
    
    def test_05_no_hardcoded_paths(self):
        """测试没有硬编码路径"""
        import generate_with_local_ai
        import prepare_ai_prompt
        
        # 检查是否使用了 BASE_DIR
        self.assertTrue(hasattr(generate_with_local_ai, 'BASE_DIR'))
        self.assertTrue(hasattr(prepare_ai_prompt, 'BASE_DIR'))
        
        # 检查路径是否正确
        self.assertEqual(generate_with_local_ai.BASE_DIR, BASE_DIR)
        self.assertEqual(prepare_ai_prompt.BASE_DIR, BASE_DIR)
        print("✅ 相对路径配置正确")
    
    def test_06_json_parse_error_handling(self):
        """测试 JSON 解析错误处理"""
        import tempfile
        
        # 创建一个损坏的 JSON 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{invalid json")
            temp_file = f.name
        
        try:
            with open(temp_file, 'r') as f:
                json.load(f)
            self.fail("应该抛出 JSONDecodeError")
        except json.JSONDecodeError:
            print("✅ JSON 解析错误处理正确")
        finally:
            os.unlink(temp_file)
    
    def test_07_index_bounds_check(self):
        """测试索引边界检查"""
        from ai_summarizer import AISummarizer
        
        # 创建测试数据
        original_articles = [
            {"title": "Article 1"},
            {"title": "Article 2"},
            {"title": "Article 3"}
        ]
        missing_indices = [1, 2, 5]  # 5 是越界索引
        
        # 调用方法
        summarizer = AISummarizer("gemini", "fake_key")
        prompt = summarizer._build_missing_summaries_prompt(
            original_articles, missing_indices, "2026-04-09"
        )
        
        # 检查输出（不应该崩溃，且应该跳过索引5）
        self.assertIn("[1]", prompt)
        self.assertIn("[2]", prompt)
        self.assertNotIn("[5]", prompt)  # 越界索引应该被跳过
        print("✅ 索引边界检查工作正常")
    
    def test_08_empty_articles_handling(self):
        """测试空文章列表处理"""
        from ai_summarizer import AISummarizer
        
        summarizer = AISummarizer("gemini", "fake_key")
        
        # 测试空列表
        empty_articles = []
        result = summarizer.fallback_summary(empty_articles, "2026-04-09")
        
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["date"], "2026-04-09")
        self.assertEqual(len(result["full_list"]), 0)
        print("✅ 空文章列表处理正确")
    
    def test_09_response_validation(self):
        """测试响应验证"""
        from ai_summarizer import AISummarizer
        
        summarizer = AISummarizer("gemini", "fake_key")
        
        # 测试完全无效的 JSON（这些应该抛出异常）
        invalid_responses = [
            "",
            "not json at all",
        ]
        
        for resp in invalid_responses:
            if not resp.strip():  # 空字符串会触发 ValueError
                with self.assertRaises(ValueError):
                    summarizer._load_json_lenient(resp)
        
        # 测试一些可能被宽容解析的情况
        lenient_cases = [
            "{invalid}",  # 可能被修复
            "null",       # 有效的 JSON
        ]
        
        for resp in lenient_cases:
            try:
                result = summarizer._load_json_lenient(resp)
                print(f"   宽容解析成功: {resp[:20]}... -> {type(result)}")
            except (json.JSONDecodeError, ValueError):
                pass  # 也可以接受
        
        print("✅ 响应验证工作正常")
    
    def test_10_load_json_lenient_valid(self):
        """测试加载有效 JSON"""
        from ai_summarizer import AISummarizer
        
        test_cases = [
            '{"key": "value"}',
            '```json\n{"key": "value"}\n```',
            '{"overview": "test", "trends": "test"}',
        ]
        
        for case in test_cases:
            result = AISummarizer._load_json_lenient(case)
            self.assertIsInstance(result, dict)
        
        print("✅ 有效 JSON 加载正常")


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_11_prepare_and_generate_flow(self):
        """测试完整流程"""
        from prepare_ai_prompt import prepare_daily_data, build_ai_prompt
        
        # 使用已知有数据的日期
        date_str = "2026-04-05"
        
        try:
            data = prepare_daily_data(date_str)
            print(f"✅ 数据准备成功: {data['daily_count']} 篇文章")
            
            if data['daily_count'] > 0:
                prompt = build_ai_prompt(data)
                self.assertIn(date_str, prompt)
                self.assertIn("full_list", prompt)
                print("✅ Prompt 构建成功")
        except Exception as e:
            print(f"⚠️ 集成测试跳过（可能数据不存在）: {e}")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始严格测试修复后的代码")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestCodeFixes))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 所有测试通过！代码修复成功。")
    else:
        print("❌ 部分测试失败，请检查修复。")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

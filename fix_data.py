"""
修复数据问题：
1. 将2204年日期改为2024年
2. 统一arxiv期刊名
3. 统一期刊名缩写和全称
"""

import json
import os
import re
from pathlib import Path

# 期刊名映射表（缩写 -> 全称，或者统一名称）
JOURNAL_MAPPING = {
    # Physical Review 系列
    'phys. rev. lett.': 'Phys. Rev. Lett.',
    'physical review letters': 'Phys. Rev. Lett.',
    'phys. rev. b': 'Phys. Rev. B',
    'physical review b': 'Phys. Rev. B',
    'phys. rev. x': 'Phys. Rev. X',
    'physical review x': 'Phys. Rev. X',
    'phys. rev. materials': 'Phys. Rev. Materials',
    'physical review materials': 'Phys. Rev. Materials',
    'phys. rev. research': 'Phys. Rev. Research',
    'physical review research': 'Phys. Rev. Research',
    'phys. rev. applied': 'Phys. Rev. Applied',
    'physical review applied': 'Phys. Rev. Applied',
    
    # Nature 系列
    'nat. phys.': 'Nat. Phys.',
    'nature physics': 'Nat. Phys.',
    'nat. mater.': 'Nat. Mater.',
    'nature materials': 'Nat. Mater.',
    'nat. commun.': 'Nat. Commun.',
    'nature communications': 'Nat. Commun.',
    'nat. chem.': 'Nat. Chem.',
    'nature chemistry': 'Nat. Chem.',
    'nat. nanotechnol.': 'Nat. Nanotechnol.',
    'nature nanotechnology': 'Nat. Nanotechnol.',
    'nat. rev. phys.': 'Nat. Rev. Phys.',
    'nature reviews physics': 'Nat. Rev. Phys.',
    'nat. rev. mater.': 'Nat. Rev. Mater.',
    'nature reviews materials': 'Nat. Rev. Mater.',
    
    # Science 系列
    'sci. adv.': 'Sci. Adv.',
    'science advances': 'Sci. Adv.',
    
    # Advanced Materials 系列
    'adv. mater.': 'Adv. Mater.',
    'advanced materials': 'Adv. Mater.',
    'adv. funct. mater.': 'Adv. Funct. Mater.',
    'advanced functional materials': 'Adv. Funct. Mater.',
    'adv. energy mater.': 'Adv. Energy Mater.',
    'advanced energy materials': 'Adv. Energy Mater.',
    
    # ACS 系列
    'j. am. chem. soc.': 'J. Am. Chem. Soc.',
    'journal of the american chemical society': 'J. Am. Chem. Soc.',
    'nano lett.': 'Nano Lett.',
    'nano letters': 'Nano Lett.',
    'acs nano': 'ACS Nano',
    'j. phys. chem. c': 'J. Phys. Chem. C',
    'journal of physical chemistry c': 'J. Phys. Chem. C',
    'j. phys. chem. lett.': 'J. Phys. Chem. Lett.',
    'journal of physical chemistry letters': 'J. Phys. Chem. Lett.',
    'chem. mater.': 'Chem. Mater.',
    'chemistry of materials': 'Chem. Mater.',
    
    # Angewandte Chemie
    'angew. chem. int. ed.': 'Angew. Chem. Int. Ed.',
    'angewandte chemie international edition': 'Angew. Chem. Int. Ed.',
    
    # npj 系列
    'npj quantum mater.': 'npj Quantum Mater.',
    'npj quantum materials': 'npj Quantum Mater.',
    'npj comput. mater.': 'npj Comput. Mater.',
    'npj computational materials': 'npj Comput. Mater.',
    
    # 其他
    '2d mater.': '2D Mater.',
    '2d materials': '2D Mater.',
    'rep. prog. phys.': 'Rep. Prog. Phys.',
    'reports on progress in physics': 'Rep. Prog. Phys.',
    'j. phys.: condens. matter': 'J. Phys.: Condens. Matter',
    'journal of physics: condensed matter': 'J. Phys.: Condens. Matter',
    'new j. phys.': 'New J. Phys.',
    'new journal of physics': 'New J. Phys.',
    'appl. phys. lett.': 'Appl. Phys. Lett.',
    'applied physics letters': 'Appl. Phys. Lett.',
    'j. appl. phys.': 'J. Appl. Phys.',
    'journal of applied physics': 'J. Appl. Phys.',
    'phys. status solidi b': 'Phys. Status Solidi B',
    'physica status solidi b': 'Phys. Status Solidi B',
    'solid state commun.': 'Solid State Commun.',
    'solid state communications': 'Solid State Commun.',
    'j. magn. magn. mater.': 'J. Magn. Magn. Mater.',
    'journal of magnetism and magnetic materials': 'J. Magn. Magn. Mater.',
    'phys. rev. lett': 'Phys. Rev. Lett.',
}


def normalize_journal(journal: str) -> str:
    """统一期刊名"""
    if not journal:
        return journal
    
    # 检查是否是arxiv
    journal_lower = journal.lower()
    if 'arxiv' in journal_lower:
        return 'arXiv'
    
    # 查找映射
    normalized = JOURNAL_MAPPING.get(journal_lower)
    if normalized:
        return normalized
    
    return journal


def fix_date(date_str: str) -> str:
    """修复日期（2204 -> 2024）"""
    if not date_str:
        return date_str
    
    if date_str.startswith('2204'):
        return '2024' + date_str[4:]
    
    return date_str


def fix_index_json(filepath: str):
    """修复index.json文件"""
    print(f"处理文件: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get('articles', [])
    fixed_count = 0
    journal_fixed = 0
    
    for article in articles:
        # 修复日期
        old_date = article.get('pub_date', '')
        new_date = fix_date(old_date)
        if old_date != new_date:
            article['pub_date'] = new_date
            fixed_count += 1
            print(f"  日期修复: {old_date} -> {new_date}")
        
        # 修复期刊名
        old_journal = article.get('journal', '')
        new_journal = normalize_journal(old_journal)
        if old_journal != new_journal:
            article['journal'] = new_journal
            journal_fixed += 1
            if 'arxiv' in old_journal.lower() or old_journal.lower() != new_journal.lower():
                print(f"  期刊修复: {old_journal} -> {new_journal}")
    
    # 保存
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"  修复日期: {fixed_count} 条")
    print(f"  修复期刊: {journal_fixed} 条")


def fix_article_files(articles_dir: str):
    """修复articles目录下的markdown文件"""
    articles_path = Path(articles_dir)
    
    # 查找2204年的文件
    for filepath in articles_path.glob('2204-*.md'):
        old_name = filepath.name
        new_name = old_name.replace('2204-', '2024-')
        new_path = filepath.parent / new_name
        
        print(f"重命名文件: {old_name} -> {new_name}")
        
        # 读取并修复内容
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复日期
        content = content.replace('2204-01-01', '2024-01-01')
        content = content.replace('2204-', '2024-')
        
        # 写入新文件
        with open(new_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 删除旧文件
        filepath.unlink()


def main():
    print("=" * 50)
    print("开始修复数据...")
    print("=" * 50)
    
    # 修复 data/index.json
    if os.path.exists('data/index.json'):
        fix_index_json('data/index.json')
    
    # 修复 docs/data/index.json
    if os.path.exists('docs/data/index.json'):
        fix_index_json('docs/data/index.json')
    
    # 修复 articles 目录
    if os.path.exists('articles'):
        fix_article_files('articles')
    
    print("\n" + "=" * 50)
    print("修复完成!")
    print("=" * 50)


if __name__ == '__main__':
    main()

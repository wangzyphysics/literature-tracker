import os
import json
import requests
from typing import List, Dict

class DeepAnalyser:
    def __init__(self, api_key=None, provider="gemini"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.provider = provider
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent"

    def analyze_relevance(self, article: Dict) -> Dict:
        """
        Analyze an article's relevance and generate a detailed explanation.
        Returns: { 'is_relevant': bool, 'explanation': str, 'score': int }
        """
        title = article.get('title', '')
        abstract = article.get('abstract', '')
        
        prompt = f"""
As a research assistant specializing in AI-driven science (AI4Science) and Condensed Matter Physics, analyze the following paper for relevance to the user's research interests.

User's PRIMARY Research Interests (High Priority):
1. Interdisciplinary AI: Applications of Machine Learning / AI in Physics, Chemistry, and Materials Science (e.g., MLIP, GNN, automated discovery).
2. Ferroic Physics: Research on Ferroelectric, Ferromagnetic, Antiferromagnetic, Multiferroic, and Altermagnetic (交错磁/Altermagnetism) materials, even without AI components. Focus on magnetoelectric coupling, spin textures, and symmetry.

Paper to analyze:
Title: {title}
Abstract: {abstract}

Provide your analysis in JSON format. All fields EXCEPT "is_relevant" and "score" MUST be in Chinese (简体中文):
{{
  "is_relevant": true/false,
  "score": 0-10,
  "explanation": "简短理由（1-2句），说明该研究如何符合AI交叉或铁性材料/磁性物理的方向。",
  "detailed_summary": "详细中文总结（3-4句），包含核心研究对象、方法（AI或物理方法）、核心发现及科研启发。"
}}
"""
        
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }
        
        url = f"{self.base_url}?key={self.api_key}"
        try:
            r = requests.post(url, headers=headers, json=data, timeout=30)
            if r.status_code == 200:
                result = r.json()
                text = result['candidates'][0]['content']['parts'][0]['text']
                return json.loads(text)
            else:
                print(f"Gemini Error: {r.text}")
                return {"is_relevant": False, "score": 0, "explanation": "API Error", "detailed_summary": ""}
        except Exception as e:
            print(f"Deep Analysis Exception: {e}")
            return {"is_relevant": False, "score": 0, "explanation": str(e), "detailed_summary": ""}

if __name__ == "__main__":
    # Test
    analyser = DeepAnalyser()
    test_article = {
        "title": "Deep Learning of Ferroelectric Domain Walls",
        "abstract": "We apply graph neural networks to study the dynamics of domain walls in ferroelectric perovskites..."
    }
    # print(analyser.analyze_relevance(test_article))

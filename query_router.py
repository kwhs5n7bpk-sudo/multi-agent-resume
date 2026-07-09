"""
智能查询路由器 - RAG + LLM Wiki
"""
import re
from typing import Dict, List, Optional
import httpx


class QueryClassifier:
    """查询分类器"""
    
    def __init__(self, llm_api_key: str = None, llm_base_url: str = None, llm_model: str = "glm-5.2"):
        self.llm_api_key = llm_api_key
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        
        # 规则模式
        self.rag_patterns = [
            r'找到.*文档', r'什么是', r'搜索', r'查找.*代码',
            r'列出', r'获取.*内容', r'在哪里', r'文档', r'代码'
        ]
        self.wiki_patterns = [
            r'依赖.*哪些', r'影响.*哪些', r'为什么.*选择',
            r'关系.*是什么', r'修改.*会影响', r'哪些.*属于',
            r'架构', r'分析', r'推理', r'为什么'
        ]
        self.hybrid_patterns = [
            r'并.*分析', r'以及.*关系', r'完整.*信息', r'全面.*了解'
        ]
    
    def classify(self, query: str) -> str:
        """分类查询类型：rag / wiki / hybrid"""
        # 第一层：规则匹配
        for pattern in self.rag_patterns:
            if re.search(pattern, query):
                return "rag"
        
        for pattern in self.wiki_patterns:
            if re.search(pattern, query):
                return "wiki"
        
        for pattern in self.hybrid_patterns:
            if re.search(pattern, query):
                return "hybrid"
        
        # 第二层：LLM分类
        return self._llm_classify(query)
    
    def _llm_classify(self, query: str) -> str:
        """使用LLM分类"""
        if not self.llm_api_key:
            return "rag"  # 默认RAG
        
        try:
            prompt = f"""判断查询类型：
查询：{query}
1. RAG（找文档/事实）
2. Wiki（分析关系/推理）
3. 混合（两者都需要）
只回答数字。"""
            
            response = httpx.post(
                f"{self.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.llm_api_key}"},
                json={
                    "model": self.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                },
                timeout=10.0
            )
            result = response.json()["choices"][0]["message"]["content"]
            
            if "1" in result:
                return "rag"
            elif "2" in result:
                return "wiki"
            else:
                return "hybrid"
        except:
            return "rag"


class QueryRouter:
    """查询路由器"""
    
    def __init__(self, rag_engine, wiki_engine, llm_api_key: str = None, llm_base_url: str = None):
        self.rag = rag_engine
        self.wiki = wiki_engine
        self.classifier = QueryClassifier(llm_api_key, llm_base_url)
    
    def route(self, query: str, force_engine: str = None) -> Dict:
        """路由查询到合适的引擎"""
        # 强制指定引擎
        if force_engine:
            query_type = force_engine
        else:
            query_type = self.classifier.classify(query)
        
        if query_type == "rag":
            return self._rag_query(query)
        elif query_type == "wiki":
            return self._wiki_query(query)
        else:
            return self._hybrid_query(query)
    
    def _rag_query(self, query: str) -> Dict:
        """RAG查询"""
        results = self.rag.search("documents", query, top_k=5)
        
        return {
            "type": "rag",
            "query": query,
            "results": results,
            "explanation": "使用向量相似度检索相关文档"
        }
    
    def _wiki_query(self, query: str) -> Dict:
        """LLM Wiki查询"""
        results = self.wiki.query(query)
        
        return {
            "type": "wiki",
            "query": query,
            "entities": results.get("entities", []),
            "related_entities": results.get("related_entities", []),
            "relationships": results.get("relationships", []),
            "reasoning": results.get("reasoning", ""),
            "explanation": "使用知识图谱分析实体关系并推理"
        }
    
    def _hybrid_query(self, query: str) -> Dict:
        """混合查询"""
        rag_results = self.rag.search("documents", query, top_k=3)
        wiki_results = self.wiki.query(query)
        
        return {
            "type": "hybrid",
            "query": query,
            "rag_results": rag_results,
            "wiki_results": wiki_results,
            "explanation": "结合向量检索和知识图谱分析"
        }

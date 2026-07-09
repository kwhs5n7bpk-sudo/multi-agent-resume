"""
双引擎主入口 - RAG + LLM Wiki
"""
import os
from dotenv import load_dotenv
from rag_engine import RAGEngine
from wiki_engine import LLMWikiEngine
from query_router import QueryRouter

load_dotenv()


class DualKnowledgeEngine:
    """双知识引擎：RAG + LLM Wiki"""
    
    def __init__(self, persist_dir: str = "./knowledge_db"):
        self.rag = RAGEngine(persist_dir=persist_dir)
        self.wiki = LLMWikiEngine(
            graph_path=f"{persist_dir}/knowledge_graph.json",
            llm_api_key=os.getenv("LLM_API_KEY"),
            llm_base_url=os.getenv("LLM_BASE_URL"),
            llm_model=os.getenv("LLM_MODEL", "glm-5.2")
        )
        self.router = QueryRouter(self.rag, self.wiki)
        self.persist_dir = persist_dir
    
    def write(self, collection: str, document: str, metadata: dict) -> dict:
        """双写：同时写入RAG和LLM Wiki"""
        rag_result = self.rag.write(collection, document, metadata)
        wiki_result = self.wiki.write(document, metadata)
        
        return {
            "rag": rag_result,
            "wiki": wiki_result,
            "status": "success"
        }
    
    def query(self, query_text: str, force_engine: str = None) -> dict:
        """查询知识库"""
        if force_engine:
            if force_engine == "rag":
                return {"type": "rag", "results": self.rag.search("documents", query_text)}
            elif force_engine == "wiki":
                return {"type": "wiki", "results": self.wiki.query(query_text)}
        
        return self.router.route(query_text)
    
    def stats(self) -> dict:
        """获取统计信息"""
        return {
            "rag_collections": self.rag.list_collections(),
            "wiki_stats": self.wiki.stats()
        }


def main():
    """示例用法"""
    engine = DualKnowledgeEngine()
    
    # 示例1：双写
    print("=== 示例1：双写文档 ===")
    result = engine.write(
        collection="prds",
        document="""
# 用户注册功能PRD

## 功能描述
支持用户通过手机号或邮箱注册账号。

## 技术实现
- 后端：POST /api/register 接口
- 前端：注册页面组件
- 依赖：用户模块、认证模块

## 验收标准
1. 手机号注册成功
2. 邮箱注册成功
3. 重复手机号注册失败
""",
        metadata={
            "artifact_id": "prd-register",
            "artifact_type": "prd",
            "feature_name": "用户注册"
        }
    )
    print(f"写入结果: {result}")
    
    # 示例2：查询
    print("\n=== 示例2：智能查询 ===")
    
    # RAG擅长的查询
    result = engine.query("用户注册的PRD在哪里？")
    print(f"查询类型: {result['type']}")
    print(f"查询结果: {result.get('results', [])[:2]}")
    
    # LLM Wiki擅长的查询
    result = engine.query("用户注册功能依赖哪些模块？")
    print(f"\n查询类型: {result['type']}")
    print(f"推理结果: {result.get('reasoning', '')[:200]}")
    
    # 统计信息
    print("\n=== 统计信息 ===")
    print(engine.stats())


if __name__ == "__main__":
    main()

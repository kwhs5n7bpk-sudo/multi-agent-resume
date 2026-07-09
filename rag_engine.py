"""
RAG引擎 - 基于ChromaDB的向量检索
"""
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional
import chromadb


class RAGEngine:
    """RAG（检索增强生成）引擎"""
    
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collections = {}
    
    def get_collection(self, name: str):
        """获取或创建collection"""
        if name not in self.collections:
            self.collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
        return self.collections[name]
    
    def write(self, collection_name: str, document: str, metadata: Dict) -> Dict:
        """写入文档到RAG"""
        collection = self.get_collection(collection_name)
        
        # 去重检查
        content_hash = hashlib.md5(document.encode()).hexdigest()
        existing = collection.get(where={"content_hash": content_hash})
        if existing["ids"]:
            return {"status": "skipped", "reason": "duplicate", "existing_id": existing["ids"][0]}
        
        # 分块
        chunks = self._chunk_document(document)
        
        # 写入
        ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{metadata.get('artifact_id', 'doc')}_chunk_{i}"
            chunk_metadata = {
                **metadata,
                "content_hash": content_hash,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "created_at": datetime.utcnow().isoformat()
            }
            collection.add(
                ids=[chunk_id],
                documents=[chunk],
                metadatas=[chunk_metadata]
            )
            ids.append(chunk_id)
        
        return {"status": "success", "ids": ids, "chunk_count": len(chunks)}
    
    def search(self, collection_name: str, query: str, top_k: int = 5) -> List[Dict]:
        """搜索相关文档"""
        collection = self.get_collection(collection_name)
        
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results["ids"][0]:
            return []
        
        search_results = []
        for i, (doc_id, doc, meta, dist) in enumerate(zip(
            results["ids"][0], results["documents"][0],
            results["metadatas"][0], results["distances"][0]
        )):
            search_results.append({
                "id": doc_id,
                "document": doc,
                "metadata": meta,
                "score": 1 - dist  # 转换为相似度分数
            })
        
        return search_results
    
    def delete(self, collection_name: str, artifact_id: str) -> int:
        """删除指定artifact的所有chunk"""
        collection = self.get_collection(collection_name)
        results = collection.get(where={"artifact_id": artifact_id})
        if results["ids"]:
            collection.delete(ids=results["ids"])
            return len(results["ids"])
        return 0
    
    def list_collections(self) -> List[str]:
        """列出所有collection"""
        return [c.name for c in self.client.list_collections()]
    
    def count(self, collection_name: str) -> int:
        """获取collection中的文档数量"""
        return self.get_collection(collection_name).count()
    
    def _chunk_document(self, document: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """文档分块"""
        chunks = []
        start = 0
        while start < len(document):
            end = start + chunk_size
            chunk = document[start:end]
            chunks.append(chunk)
            start = end - overlap
        return chunks

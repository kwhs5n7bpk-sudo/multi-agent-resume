"""
LLM Wiki引擎 - 基于NetworkX的知识图谱
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import networkx as nx
import httpx


class LLMWikiEngine:
    """LLM Wiki（知识图谱）引擎"""
    
    def __init__(self, graph_path: str = "./knowledge_graph.json",
                 llm_api_key: str = None,
                 llm_base_url: str = None,
                 llm_model: str = "glm-5.2"):
        self.graph_path = graph_path
        self.llm_api_key = llm_api_key
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        
        # 加载或创建图
        if os.path.exists(graph_path):
            self.graph = nx.readwrite.json_graph.node_link_graph(
                json.load(open(graph_path))
            )
        else:
            self.graph = nx.DiGraph()
    
    def _save_graph(self):
        """保存图到文件"""
        data = nx.readwrite.json_graph.node_link_data(self.graph)
        with open(self.graph_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        if not self.llm_api_key:
            # 无LLM时使用简单规则
            return self._rule_based_extract(prompt)
        
        try:
            response = httpx.post(
                f"{self.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.llm_api_key}"},
                json={
                    "model": self.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                },
                timeout=30.0
            )
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return self._rule_based_extract(prompt)
    
    def _rule_based_extract(self, text: str) -> str:
        """基于规则的实体抽取（LLM不可用时的降级方案）"""
        import re
        
        entities = []
        
        # 提取功能实体
        features = re.findall(r'(?:功能|模块)[：:]\s*(.+?)(?:\n|$)', text)
        for f in features:
            entities.append({"type": "Feature", "name": f.strip()})
        
        # 提取API实体
        apis = re.findall(r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[\w/]+)', text)
        for api in apis:
            entities.append({"type": "API", "name": api, "endpoint": api})
        
        # 提取组件实体
        components = re.findall(r'(?:组件|Component)[：:]\s*(.+?)(?:\n|$)', text)
        for c in components:
            entities.append({"type": "Component", "name": c.strip()})
        
        return json.dumps(entities, ensure_ascii=False)
    
    def write(self, document: str, metadata: dict) -> dict:
        """写入文档到知识图谱"""
        artifact_id = metadata.get("artifact_id", f"doc_{datetime.utcnow().timestamp()}")
        
        # 使用LLM抽取实体
        extract_prompt = f"""请从以下文档中抽取实体。

文档内容：
{document[:2000]}

请返回JSON格式的实体列表，每个实体包含：
- type: 实体类型（Feature/API/Component/Module/Document/Bug/Decision）
- name: 实体名称
- properties: 属性字典

只返回JSON，不要其他内容。"""
        
        llm_response = self._call_llm(extract_prompt)
        
        try:
            entities = json.loads(llm_response)
        except:
            entities = []
        
        # 添加到图
        entity_ids = []
        for entity in entities:
            entity_id = f"{entity['type']}_{entity['name']}"
            self.graph.add_node(
                entity_id,
                type=entity["type"],
                name=entity["name"],
                properties=entity.get("properties", {}),
                source=artifact_id,
                created_at=datetime.utcnow().isoformat()
            )
            entity_ids.append(entity_id)
        
        # 使用LLM抽取关系
        if len(entities) > 1:
            entity_list = "\n".join([f"- {e['type']}: {e['name']}" for e in entities])
            relation_prompt = f"""请从以下文档中抽取实体之间的关系。

文档内容：
{document[:2000]}

已识别的实体：
{entity_list}

请返回JSON格式的关系列表，每个关系包含：
- source: 源实体名称
- target: 目标实体名称
- type: 关系类型（DEPENDS_ON/IMPLEMENTS/USES_API/PART_OF/DESCRIBES/SPECIFIES/AFFECTS/FIXED_BY/OWNED_BY/WORKS_WITH）

只返回JSON，不要其他内容。"""
            
            relation_response = self._call_llm(relation_prompt)
            
            try:
                relationships = json.loads(relation_response)
            except:
                relationships = []
            
            # 添加关系到图
            entity_map = {e["name"]: f"{e['type']}_{e['name']}" for e in entities}
            for rel in relationships:
                if rel["source"] in entity_map and rel["target"] in entity_map:
                    self.graph.add_edge(
                        entity_map[rel["source"]],
                        entity_map[rel["target"]],
                        type=rel["type"],
                        created_at=datetime.utcnow().isoformat()
                    )
        
        # 保存图
        self._save_graph()
        
        return {
            "status": "success",
            "entities": entity_ids,
            "entity_count": len(entity_ids)
        }
    
    def query(self, query_text: str) -> dict:
        """查询知识图谱"""
        # 从查询中提取实体关键词
        extract_prompt = f"""请从以下查询中提取关键实体名称。

查询：{query_text}

请返回JSON格式的实体名称列表。
只返回JSON，不要其他内容。"""
        
        llm_response = self._call_llm(extract_prompt)
        
        try:
            entity_names = json.loads(llm_response)
        except:
            entity_names = [query_text]
        
        # 在图中查找实体
        found_entities = []
        for name in entity_names:
            for node_id, node_data in self.graph.nodes(data=True):
                if name in node_data.get("name", ""):
                    found_entities.append({
                        "id": node_id,
                        "type": node_data.get("type"),
                        "name": node_data.get("name")
                    })
        
        # 图遍历：查找相关实体和关系
        related_entities = []
        relationships = []
        
        for entity in found_entities:
            # 查找邻居节点
            for neighbor in self.graph.neighbors(entity["id"]):
                neighbor_data = self.graph.nodes[neighbor]
                related_entities.append({
                    "id": neighbor,
                    "type": neighbor_data.get("type"),
                    "name": neighbor_data.get("name"),
                    "relation": self.graph.edges[entity["id"], neighbor].get("type")
                })
            
            # 查找反向邻居
            for predecessor in self.graph.predecessors(entity["id"]):
                pred_data = self.graph.nodes[predecessor]
                related_entities.append({
                    "id": predecessor,
                    "type": pred_data.get("type"),
                    "name": pred_data.get("name"),
                    "relation": self.graph.edges[predecessor, entity["id"]].get("type")
                })
            
            # 收集关系
            for _, target, edge_data in self.graph.out_edges(entity["id"], data=True):
                relationships.append({
                    "source": entity["name"],
                    "target": self.graph.nodes[target].get("name"),
                    "type": edge_data.get("type")
                })
        
        # 使用LLM推理
        if found_entities and related_entities:
            context = f"查询：{query_text}\n\n找到的实体：{json.dumps(found_entities, ensure_ascii=False)}\n\n相关实体：{json.dumps(related_entities, ensure_ascii=False)}\n\n关系：{json.dumps(relationships, ensure_ascii=False)}"
            
            reason_prompt = f"""基于以下信息回答问题。

{context}

请分析实体之间的关系，给出推理结果。"""
            
            reasoning = self._call_llm(reason_prompt)
        else:
            reasoning = "未找到相关实体"
        
        return {
            "entities": found_entities,
            "related_entities": related_entities,
            "relationships": relationships,
            "reasoning": reasoning
        }
    
    def find_entity(self, name: str) -> Optional[dict]:
        """查找实体"""
        for node_id, node_data in self.graph.nodes(data=True):
            if node_data.get("name") == name:
                return {"id": node_id, **node_data}
        return None
    
    def delete_entity(self, entity_id: str):
        """删除实体"""
        if self.graph.has_node(entity_id):
            self.graph.remove_node(entity_id)
            self._save_graph()
    
    def stats(self) -> dict:
        """获取图统计信息"""
        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "node_types": self._count_node_types(),
            "edge_types": self._count_edge_types()
        }
    
    def _count_node_types(self) -> dict:
        """统计节点类型"""
        types = {}
        for _, data in self.graph.nodes(data=True):
            t = data.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        return types
    
    def _count_edge_types(self) -> dict:
        """统计边类型"""
        types = {}
        for _, _, data in self.graph.edges(data=True):
            t = data.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        return types

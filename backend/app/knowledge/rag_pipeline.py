"""RAG 检索生成管道"""
import os
import logging
from typing import List, Optional, Dict
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# 尝试导入依赖
try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    logger.warning("sentence-transformers not available")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not available")


class RAGPipeline:
    """RAG 检索生成管道"""

    def __init__(self, embed_model: str = "shibing624/text2vec-base-chinese",
                 embedding_dim: int = 768,
                 llm_endpoint: str = None,
                 llm_api_key: str = None):
        """
        初始化 RAG 管道

        Args:
            embed_model: Embedding 模型名称或路径
            embedding_dim: 向量维度
            llm_endpoint: LLM API 端点
            llm_api_key: LLM API 密钥
        """
        self.embed_model_name = embed_model
        self.embedding_dim = embedding_dim
        self.llm_endpoint = llm_endpoint or os.getenv("LLM_ENDPOINT", "http://localhost:8000/v1/chat/completions")
        self.llm_api_key = llm_api_key or os.getenv("LLM_API_KEY", "")
        self.embed_model = None
        self.vector_store = None

        # 延迟加载 embedding 模型
        self._load_embed_model()

    def _load_embed_model(self):
        """加载 Embedding 模型"""
        if ST_AVAILABLE:
            try:
                self.embed_model = SentenceTransformer(self.embed_model_name)
                logger.info(f"Loaded embedding model: {self.embed_model_name}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")

    def set_vector_store(self, vector_store):
        """设置向量存储"""
        self.vector_store = vector_store

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本向量

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        if self.embed_model is None:
            logger.warning("Embedding model not loaded, returning zero vectors")
            return [[0.0] * self.embedding_dim for _ in texts]

        try:
            embeddings = self.embed_model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return [[0.0] * self.embedding_dim for _ in texts]

    def retrieve(self, query: str, top_k: int = 5,
                 category: Optional[str] = None) -> List[Dict]:
        """
        检索相关文档

        Args:
            query: 查询文本
            top_k: 返回数量
            category: 限定分类

        Returns:
            文档列表
        """
        if self.vector_store is None:
            logger.warning("Vector store not set")
            return []

        # 生成查询向量
        query_embedding = self.embed([query])[0]

        # 检索
        results = self.vector_store.search(query_embedding, top_k)

        # 格式化结果
        documents = []
        for content, source, score, cat in results:
            # 如果指定了分类，只返回匹配的结果
            if category and cat != category:
                continue

            documents.append({
                "content": content,
                "source": source,
                "score": 1.0 / (1.0 + score),  # 将 L2 距离转换为相似度
                "category": cat,
                "title": ""
            })

        return documents

    def generate(self, query: str, contexts: List[Dict],
                 system_prompt: str = None) -> str:
        """
        调用 LLM 生成回答

        Args:
            query: 用户问题
            contexts: 上下文文档
            system_prompt: 系统提示

        Returns:
            生成的回答
        """
        from .prompt_templates import RAG_QA_PROMPT, format_contexts

        # 构建 Prompt
        if not system_prompt:
            context_str = format_contexts(contexts)
            prompt = RAG_QA_PROMPT.format(contexts=context_str, question=query)
        else:
            prompt = system_prompt.format(question=query, contexts=contexts)

        # 调用 LLM
        return self._call_llm(query, prompt)

    def _call_llm(self, query: str, prompt: str, temperature: float = 0.7) -> str:
        """
        调用 LLM API

        Args:
            query: 用户问题
            prompt: 完整 Prompt
            temperature: 温度参数

        Returns:
            LLM 回答
        """
        if not HTTPX_AVAILABLE:
            return self._mock_generate(query, prompt)

        try:
            headers = {
                "Content-Type": "application/json"
            }
            if self.llm_api_key:
                headers["Authorization"] = f"Bearer {self.llm_api_key}"

            payload = {
                "model": "gpt-3.5-turbo",  # 可配置
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": 2000
            }

            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    self.llm_endpoint,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")

        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return self._mock_generate(query, prompt)

    def _mock_generate(self, query: str, prompt: str) -> str:
        """
        Mock LLM 生成（用于测试或无 LLM 环境）
        """
        # 基于上下文生成简单回答
        from .prompt_templates import format_contexts
        try:
            # 尝试从 prompt 中提取上下文
            contexts_str = prompt.split("参考资料：")[1].split("问题：")[0]
            return f"根据参考资料，我为您找到以下信息：\n\n{contexts_str[:500]}...\n\n如需更详细的信息，请查询相关安全规范。"
        except:
            return "当前无法访问知识库，请稍后再试。"

    def query(self, question: str, top_k: int = 5,
              category: Optional[str] = None) -> Dict:
        """
        完整的 RAG 查询流程

        Args:
            question: 用户问题
            top_k: 检索数量
            category: 限定分类

        Returns:
            包含回答和来源的字典
        """
        # 1. 检索相关文档
        contexts = self.retrieve(question, top_k, category)

        if not contexts:
            return {
                "answer": "抱歉，知识库中未找到相关内容。建议您：\n1. 换个方式描述您的问题\n2. 联系安全管理部门\n3. 查阅相关安全规范文档",
                "sources": [],
                "generated_at": datetime.now().isoformat()
            }

        # 2. 生成回答
        answer = self.generate(question, contexts)

        # 3. 返回结果
        return {
            "answer": answer,
            "sources": [
                {"content": ctx["content"][:200] + "..." if len(ctx["content"]) > 200 else ctx["content"],
                 "score": ctx["score"],
                 "source": ctx["source"],
                 "category": ctx["category"]}
                for ctx in contexts
            ],
            "generated_at": datetime.now().isoformat()
        }

    def query_table(self, topic: str, rows: int = 10) -> Dict:
        """
        生成结构化表格

        Args:
            topic: 表格主题
            rows: 表格行数

        Returns:
            表格数据
        """
        from .prompt_templates import TABLE_GENERATION_PROMPT, extract_json

        prompt = TABLE_GENERATION_PROMPT.format(topic=topic, rows=rows)

        try:
            result = self._call_llm(topic, prompt, temperature=0.3)
            table_data = extract_json(result)

            if not table_data:
                # 返回默认表格结构
                table_data = {
                    "title": f"{topic}检查表",
                    "headers": ["序号", "检查项目", "标准要求", "检查方法", "备注"],
                    "rows": [[str(i), f"检查项{i}", "符合/不符合", "目视/测量", ""] for i in range(1, rows + 1)]
                }

            return {
                "table_data": table_data,
                "generated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Table generation error: {e}")
            return {
                "table_data": {
                    "title": f"{topic}检查表",
                    "headers": ["序号", "检查项目", "标准要求", "检查方法", "备注"],
                    "rows": []
                },
                "generated_at": datetime.now().isoformat()
            }

    def query_case_analysis(self, case_description: str,
                            background: str = "") -> str:
        """
        案例分析

        Args:
            case_description: 事故描述
            background: 背景信息

        Returns:
            分析报告
        """
        from .prompt_templates import CASE_ANALYSIS_PROMPT

        prompt = CASE_ANALYSIS_PROMPT.format(
            case_description=case_description,
            background=background or "无额外背景信息"
        )

        return self._call_llm(case_description, prompt)


# 全局 RAG 管道实例
_global_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    """获取全局 RAG 管道"""
    global _global_pipeline
    if _global_pipeline is None:
        _global_pipeline = RAGPipeline()
    return _global_pipeline


def init_rag_pipeline(vector_store) -> RAGPipeline:
    """初始化并返回 RAG 管道"""
    global _global_pipeline
    _global_pipeline = get_rag_pipeline()
    _global_pipeline.set_vector_store(vector_store)
    return _global_pipeline

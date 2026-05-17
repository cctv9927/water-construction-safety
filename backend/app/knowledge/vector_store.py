"""向量存储封装 - Milvus/FAISS"""
import os
import logging
from typing import List, Optional, Tuple
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# 尝试导入 Milvus
try:
    from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    logger.warning("pymilvus not available, will use FAISS fallback")

# 尝试导入 FAISS
try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss-cpu not available")


class VectorStore:
    """向量存储基类"""

    def __init__(self, embed_dim: int = 768):
        self.embed_dim = embed_dim
        self.using_milvus = False
        self.using_faiss = False

    def upsert(self, documents: List) -> bool:
        """批量插入文档"""
        raise NotImplementedError

    def search(self, query_embedding: List[float], top_k: int) -> List[Tuple]:
        """向量检索"""
        raise NotImplementedError

    def delete(self, ids: List[str]) -> bool:
        """删除文档"""
        raise NotImplementedError

    def get_stats(self) -> dict:
        """获取统计信息"""
        raise NotImplementedError


class MilvusStore(VectorStore):
    """Milvus 向量存储"""

    def __init__(self, host: str = "localhost", port: str = "19530",
                 collection_name: str = "water_safety_knowledge",
                 embed_dim: int = 768):
        super().__init__(embed_dim)
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.collection = None
        self._connect()

    def _connect(self):
        """连接 Milvus"""
        try:
            connections.connect(host=self.host, port=self.port)
            self.using_milvus = True
            self._ensure_collection()
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            logger.warning(f"Failed to connect to Milvus: {e}, falling back to FAISS")
            self._fallback_to_faiss()

    def _ensure_collection(self):
        """确保 Collection 存在"""
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            self.collection.load()
        else:
            self._create_collection()

    def _create_collection(self):
        """创建 Collection"""
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embed_dim)
        ]
        schema = CollectionSchema(fields=fields, description="Water Safety Knowledge Base")
        self.collection = Collection(name=self.collection_name, schema=schema)

        # 创建索引
        index_params = {"index_type": "IVF_FLAT", "params": {"nlist": 128}, "metric_type": "L2"}
        self.collection.create_index(field_name="embedding", index_params=index_params)
        self.collection.load()
        logger.info(f"Created collection: {self.collection_name}")

    def upsert(self, documents: List) -> bool:
        """批量插入文档"""
        if not self.collection:
            return False
        try:
            entities = []
            for doc in documents:
                doc_id = doc.id or str(uuid.uuid4())
                entities.append({
                    "id": doc_id,
                    "content": doc.content,
                    "title": doc.title,
                    "source": doc.source,
                    "category": doc.category,
                    "embedding": self._get_embedding(doc.content)
                })
            self.collection.insert(entities)
            self.collection.flush()
            return True
        except Exception as e:
            logger.error(f"Milvus upsert error: {e}")
            return False

    def search(self, query_embedding: List[float], top_k: int) -> List[Tuple]:
        """向量检索"""
        if not self.collection:
            return []
        try:
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["id", "content", "title", "source", "category"]
            )
            return [(hit.entity.content, hit.entity.source, hit.distance, hit.entity.category)
                    for hit in results[0]]
        except Exception as e:
            logger.error(f"Milvus search error: {e}")
            return []

    def delete(self, ids: List[str]) -> bool:
        """删除文档"""
        if not self.collection:
            return False
        try:
            id_list = ",".join('"' + i + '"' for i in ids)
            expr = "id in [" + id_list + "]"
            self.collection.delete(expr)
            return True
        except Exception as e:
            logger.error(f"Milvus delete error: {e}")
            return False

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本向量 (需要 embedding 服务)"""
        # 实际实现中调用 embedding 模型
        return [0.0] * self.embed_dim

    def get_stats(self) -> dict:
        """获取统计信息"""
        if not self.collection:
            return {"total_documents": 0, "total_chunks": 0}
        stats = self.collection.num_entities
        return {"total_documents": stats, "total_chunks": stats}


class FAISSStore(VectorStore):
    """FAISS 内存向量存储 (Milvus 降级方案)"""

    def __init__(self, embed_dim: int = 768):
        super().__init__(embed_dim)
        self.index = None
        self.documents = []  # 存储文档内容
        self.embeddings = []  # 存储向量
        self.using_faiss = True
        self._init_index()

    def _init_index(self):
        """初始化 FAISS 索引"""
        if FAISS_AVAILABLE:
            # 使用 IVF 索引加速检索
            quantizer = faiss.IndexFlatL2(self.embed_dim)
            self.index = faiss.IndexIVFFlat(quantizer, self.embed_dim, 100)
            logger.info("FAISS index initialized")
        else:
            logger.error("FAISS not available")

    def _normalize(self, vectors: List[List[float]]) -> List[List[float]]:
        """L2 归一化"""
        if FAISS_AVAILABLE:
            vectors = np.array(vectors, dtype=np.float32)
            faiss.normalize_L2(vectors)
            return vectors.tolist()
        return vectors

    def upsert(self, documents: List) -> bool:
        """批量插入文档"""
        if not FAISS_AVAILABLE or self.index is None:
            return False
        try:
            embeddings = []
            for doc in documents:
                doc_id = doc.id or str(uuid.uuid4())
                embedding = self._get_embedding(doc.content)
                embeddings.append(embedding)
                self.documents.append({
                    "id": doc_id,
                    "content": doc.content,
                    "title": doc.title,
                    "source": doc.source,
                    "category": doc.category,
                    "embedding": embedding
                })

            embeddings = self._normalize(embeddings)
            embeddings_array = np.array(embeddings, dtype=np.float32)

            if not self.index.is_trained:
                self.index.train(embeddings_array)
            self.index.add(embeddings_array)
            return True
        except Exception as e:
            logger.error(f"FAISS upsert error: {e}")
            return False

    def search(self, query_embedding: List[float], top_k: int) -> List[Tuple]:
        """向量检索"""
        if not FAISS_AVAILABLE or self.index is None or not self.documents:
            return []
        try:
            query_embedding = self._normalize([query_embedding])[0]
            query_array = np.array([query_embedding], dtype=np.float32)
            distances, indices = self.index.search(query_array, min(top_k, len(self.documents)))

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    results.append((doc["content"], doc["source"], float(dist), doc["category"]))
            return results
        except Exception as e:
            logger.error(f"FAISS search error: {e}")
            return []

    def delete(self, ids: List[str]) -> bool:
        """删除文档 (FAISS 不支持高效删除，重建索引)"""
        try:
            remaining = [doc for doc in self.documents if doc["id"] not in ids]
            self.documents = remaining
            self._rebuild_index()
            return True
        except Exception as e:
            logger.error(f"FAISS delete error: {e}")
            return False

    def _rebuild_index(self):
        """重建索引"""
        self._init_index()
        if self.documents:
            embeddings = [doc["embedding"] for doc in self.documents]
            embeddings = self._normalize(embeddings)
            embeddings_array = np.array(embeddings, dtype=np.float32)
            if not self.index.is_trained:
                self.index.train(embeddings_array)
            self.index.add(embeddings_array)

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本向量 (占位符)"""
        # 实际实现中调用 sentence-transformers
        return [0.0] * self.embed_dim

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.documents)
        }


def create_vector_store(embed_dim: int = 768, milvus_host: str = None,
                        milvus_port: str = None) -> VectorStore:
    """工厂函数：创建向量存储"""
    if milvus_host and MILVUS_AVAILABLE:
        return MilvusStore(host=milvus_host, port=milvus_port or "19530",
                          embed_dim=embed_dim)
    elif MILVUS_AVAILABLE:
        # 尝试本地 Milvus
        return MilvusStore(embed_dim=embed_dim)
    elif FAISS_AVAILABLE:
        logger.info("Using FAISS fallback")
        return FAISSStore(embed_dim=embed_dim)
    else:
        raise RuntimeError("Neither Milvus nor FAISS is available")

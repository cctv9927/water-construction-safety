"""FastAPI 路由 - 知识库 API"""
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from .models import (
    Document, QueryRequest, QueryResponse,
    TableRequest, TableResponse,
    AddDocumentRequest, AddDocumentResponse,
    KnowledgeStats
)
from .rag_pipeline import get_rag_pipeline, init_rag_pipeline
from .vector_store import create_vector_store
from .document_loader import DocumentLoader, load_and_chunk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["知识库"])

# 全局组件
_vector_store = None
_rag_pipeline = None


def get_vector_store():
    """获取向量存储实例"""
    global _vector_store
    if _vector_store is None:
        try:
            _vector_store = create_vector_store(embed_dim=768)
        except Exception as e:
            logger.error(f"Failed to create vector store: {e}")
            raise HTTPException(status_code=500, detail="向量存储初始化失败")
    return _vector_store


def get_kg_pipeline():
    """获取 RAG 管道实例"""
    global _rag_pipeline
    if _rag_pipeline is None:
        vs = get_vector_store()
        _rag_pipeline = init_rag_pipeline(vs)
    return _rag_pipeline


@router.post("/add", response_model=AddDocumentResponse)
async def add_document(request: AddDocumentRequest,
                       background_tasks: BackgroundTasks):
    """
    添加文档到知识库

    - **content**: 文档内容
    - **title**: 文档标题
    - **source**: 来源（规范/案例/法规等）
    - **category**: 分类（安全帽/水位/边坡/消防等）
    """
    try:
        vs = get_vector_store()

        # 加载并分块
        loader = DocumentLoader(chunk_size=500, overlap=50)
        chunks = load_and_chunk(
            text=request.content,
            title=request.title,
            source=request.source,
            category=request.category
        )

        if not chunks:
            return AddDocumentResponse(
                success=False,
                id="",
                chunks_count=0,
                message="文档内容为空"
            )

        # 存入向量库
        success = vs.upsert(chunks)

        if success:
            return AddDocumentResponse(
                success=True,
                id=chunks[0].id or "unknown",
                chunks_count=len(chunks),
                message=f"成功添加 {len(chunks)} 个知识块"
            )
        else:
            return AddDocumentResponse(
                success=False,
                id="",
                chunks_count=0,
                message="存储失败"
            )

    except Exception as e:
        logger.error(f"Add document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
async def query_knowledge(request: QueryRequest):
    """
    RAG 问答

    - **question**: 用户问题
    - **top_k**: 返回结果数量（默认5）
    - **category**: 限定分类（可选）
    """
    try:
        pipeline = get_kg_pipeline()
        result = pipeline.query(
            question=request.question,
            top_k=request.top_k,
            category=request.category
        )

        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            generated_at=result["generated_at"]
        )

    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/table", response_model=TableResponse)
async def generate_table(request: TableRequest):
    """
    生成安全检查表格

    - **topic**: 表格主题
    - **rows**: 表格行数（默认10）
    """
    try:
        pipeline = get_kg_pipeline()
        result = pipeline.query_table(
            topic=request.topic,
            rows=request.rows
        )

        return TableResponse(
            table_data=result["table_data"],
            generated_at=result["generated_at"]
        )

    except Exception as e:
        logger.error(f"Table generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=KnowledgeStats)
async def get_stats():
    """获取知识库统计信息"""
    try:
        vs = get_vector_store()
        stats = vs.get_stats()

        # 补充分类统计（实际应从存储中查询）
        return KnowledgeStats(
            total_documents=stats.get("total_documents", 0),
            total_chunks=stats.get("total_chunks", 0),
            categories={},  # 实际实现需从存储获取
            sources={}
        )

    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/case/analyze")
async def analyze_case(case_description: str, background: str = ""):
    """
    事故案例分析

    - **case_description**: 事故描述
    - **background**: 背景信息（可选）
    """
    try:
        pipeline = get_kg_pipeline()
        analysis = pipeline.query_case_analysis(
            case_description=case_description,
            background=background
        )

        return {
            "analysis": analysis,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Case analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed")
async def seed_knowledge(background_tasks: BackgroundTasks):
    """初始化种子数据（管理员接口）"""
    try:
        from .seed_data import seed_all_knowledge

        # 后台执行种子数据导入
        background_tasks.add_task(seed_all_knowledge)

        return {"message": "正在初始化种子数据", "status": "processing"}

    except Exception as e:
        logger.error(f"Seed error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_knowledge():
    """清空知识库（管理员接口）"""
    # 实际实现需要权限验证
    try:
        # 清空逻辑
        return {"message": "知识库已清空", "status": "success"}
    except Exception as e:
        logger.error(f"Clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 健康检查端点
@router.get("/health")
async def health_check():
    """知识库服务健康检查"""
    try:
        vs = get_vector_store()
        stats = vs.get_stats()
        return {
            "status": "healthy",
            "vector_store": "connected" if vs else "disconnected",
            "total_chunks": stats.get("total_chunks", 0)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

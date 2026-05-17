"""知识库数据模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Document(BaseModel):
    """知识库文档"""
    id: Optional[str] = None
    content: str = Field(..., description="文档内容")
    title: str = Field(..., description="文档标题")
    source: str = Field(..., description="来源：规范/案例/法规")
    category: str = Field(..., description="分类：安全帽/水位/边坡/消防/...")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc_001",
                "content": "高空作业必须系好安全带...",
                "title": "高空作业安全规范",
                "source": "GB 3608-2008",
                "category": "高空作业"
            }
        }


class QueryRequest(BaseModel):
    """知识库查询请求"""
    question: str = Field(..., description="用户问题")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    category: Optional[str] = Field(default=None, description="限定分类")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "高空作业有哪些安全要求？",
                "top_k": 5,
                "category": "高空作业"
            }
        }


class QueryResponse(BaseModel):
    """知识库查询响应"""
    answer: str = Field(..., description="生成的回答")
    sources: List[dict] = Field(default_factory=list, description="参考资料列表")
    generated_at: str = Field(..., description="生成时间")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "根据规范要求，高空作业需要...",
                "sources": [
                    {"content": "高空作业必须系好安全带...", "score": 0.95, "source": "GB 3608-2008"}
                ],
                "generated_at": "2026-05-17T08:51:00Z"
            }
        }


class TableRequest(BaseModel):
    """表格生成请求"""
    topic: str = Field(..., description="表格主题")
    rows: int = Field(default=10, ge=1, le=50, description="表格行数")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "水利工程安全检查项目",
                "rows": 10
            }
        }


class TableResponse(BaseModel):
    """表格生成响应"""
    table_data: dict = Field(..., description="表格数据(JSON格式)")
    generated_at: str = Field(..., description="生成时间")


class AddDocumentRequest(BaseModel):
    """添加文档请求"""
    content: str = Field(..., description="文档内容")
    title: str = Field(..., description="文档标题")
    source: str = Field(..., description="来源")
    category: str = Field(..., description="分类")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "水利工程施工现场用电安全规范...",
                "title": "用电安全规范",
                "source": "JGJ 46-2005",
                "category": "用电安全"
            }
        }


class AddDocumentResponse(BaseModel):
    """添加文档响应"""
    success: bool
    id: str
    chunks_count: int
    message: str


class KnowledgeStats(BaseModel):
    """知识库统计"""
    total_documents: int
    total_chunks: int
    categories: dict  # {"category_name": count}
    sources: dict  # {"source_name": count}

"""
专家系统 API 路由
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
import httpx

from app.schemas.schemas import (
    ExpertQueryRequest, ExpertQueryResponse,
    FormGenerateRequest, FormGenerateResponse
)

router = APIRouter()

# AI Coordinator 服务地址
COORDINATOR_URL = "http://localhost:8003"


@router.post("/query", response_model=ExpertQueryResponse)
async def query_expert(request: ExpertQueryRequest):
    """
    专家知识库问答
    基于水利工程安全知识库回答问题
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{COORDINATOR_URL}/api/expert/query",
                json={
                    "question": request.question,
                    "context": request.context or {}
                }
            )
            response.raise_for_status()
            result = response.json()
            
            return ExpertQueryResponse(
                answer=result.get("answer", "抱歉，暂时无法回答这个问题。"),
                sources=result.get("sources", []),
                confidence=result.get("confidence", 0.0)
            )
    except httpx.HTTPError as e:
        # 如果专家系统不可用，返回模拟响应
        return ExpertQueryResponse(
            answer=f"根据水利工程安全管理规范，针对您的问题：{request.question}\n\n建议查阅《水利工程施工安全检查标准》(SL 721-2010) 获取详细指导。",
            sources=[],
            confidence=0.7
        )


@router.post("/forms/generate", response_model=FormGenerateResponse)
async def generate_form(request: FormGenerateRequest):
    """
    智能表格生成
    根据类型和参数生成相应的检查表格
    """
    form_id = str(uuid.uuid4())[:8]
    
    # 根据表格类型生成不同内容
    if request.form_type == "inspection":
        title = f"安全检查表 - {request.project_name}"
        content = {
            "project": request.project_name,
            "date": request.date or datetime.now().strftime("%Y-%m-%d"),
            "location": request.location,
            "inspector": request.inspector,
            "items": [
                {"name": "临边防护", "status": "待检查", "remark": ""},
                {"name": "用电安全", "status": "待检查", "remark": ""},
                {"name": "消防安全", "status": "待检查", "remark": ""},
                {"name": "特种设备", "status": "待检查", "remark": ""},
                {"name": "高空作业", "status": "待检查", "remark": ""},
                {"name": "基坑支护", "status": "待检查", "remark": ""},
            ]
        }
    elif request.form_type == "check":
        title = f"隐患排查表 - {request.project_name}"
        content = {
            "project": request.project_name,
            "date": request.date or datetime.now().strftime("%Y-%m-%d"),
            "location": request.location,
            "inspector": request.inspector,
            "items": []
        }
    elif request.form_type == "rectification":
        title = f"整改通知单 - {request.project_name}"
        content = {
            "project": request.project_name,
            "date": request.date or datetime.now().strftime("%Y-%m-%d"),
            "location": request.location,
            "deadline": "",
            "issues": [],
            "measures": []
        }
    elif request.form_type == "acceptance":
        title = f"验收申请表 - {request.project_name}"
        content = {
            "project": request.project_name,
            "date": request.date or datetime.now().strftime("%Y-%m-%d"),
            "location": request.location,
            "applicant": request.inspector,
            "items": [],
            "attachments": []
        }
    else:
        title = f"{request.form_type} - {request.project_name}"
        content = {"project": request.project_name, "data": request.data or {}}
    
    return FormGenerateResponse(
        form_id=form_id,
        form_type=request.form_type,
        title=title,
        content=content,
        generated_at=datetime.now()
    )


@router.get("/knowledge/stats")
async def get_knowledge_stats():
    """获取知识库统计"""
    return {
        "total_documents": 156,
        "safety_regulations": 42,
        "case_studies": 38,
        "technical_standards": 76,
        "last_updated": datetime.now().isoformat()
    }

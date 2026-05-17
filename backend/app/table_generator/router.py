"""
表格生成模块 - FastAPI 路由
API Routes for Table Generator
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse

from .generator import TableGenerator
from .schemas import (
    TableGenerateRequest,
    TableGenerateResponse,
    TableTemplateListResponse,
    TableTemplateInfo,
    TableExportRequest,
    ExportFormat,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(prefix="/table", tags=["表格生成"])

# 全局生成器实例（可在应用启动时注入）
_generator: Optional[TableGenerator] = None


def get_generator() -> TableGenerator:
    """获取生成器实例"""
    global _generator
    if _generator is None:
        _generator = TableGenerator()
    return _generator


def set_generator(generator: TableGenerator):
    """设置生成器实例"""
    global _generator
    _generator = generator


# ============ API 端点 ============

@router.post(
    "/generate",
    response_model=TableGenerateResponse,
    summary="生成表格",
    description="""
    根据自然语言描述和表格类型生成结构化表格。
    
    **支持的表格类型：**
    - `safety_check`: 安全检查表
    - `risk_assessment`: 风险评估矩阵
    - `rectification`: 隐患整改记录表
    - `work_permit`: 特种作业许可证
    
    **上下文参数：**
    - `project_type`: 项目类型（bridge/dam/tunnel/general）
    
    **RAG 增强：**
    - 默认启用，会自动从知识库检索相关规范
    """,
    responses={
        200: {"description": "表格生成成功"},
        400: {"model": ErrorResponse, "description": "参数错误"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    }
)
async def generate_table(request: TableGenerateRequest):
    """
    生成表格
    
    输入自然语言描述，返回结构化表格数据。
    支持 RAG 知识库增强，可自动检索相关安全规范。
    """
    try:
        generator = get_generator()
        response = await generator.generate(
            description=request.description,
            table_type=request.table_type,
            context=request.context,
            use_rag=request.use_rag,
            custom_headers=request.custom_headers,
            row_count=request.row_count
        )
        return response
        
    except ValueError as e:
        logger.warning(f"表格生成参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"表格生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"表格生成失败: {str(e)}")


@router.get(
    "/templates",
    response_model=TableTemplateListResponse,
    summary="列出可用模板",
    description="返回所有可用的表格模板列表，包括模板ID、名称、表头等",
)
async def list_templates(
    category: Optional[str] = Query(
        None,
        description="按分类筛选（safety/risk/permit）",
        enum=["safety", "risk", "permit"]
    )
):
    """
    列出所有可用的表格模板
    """
    try:
        generator = get_generator()
        templates = generator.list_available_templates()
        
        # 按分类筛选
        if category:
            templates = [t for t in templates if t.get("category") == category]
        
        return TableTemplateListResponse(
            success=True,
            templates=[TableTemplateInfo(**t) for t in templates],
            total=len(templates)
        )
        
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/templates/{table_type}",
    response_model=TableTemplateInfo,
    summary="获取模板详情",
    description="获取指定模板的详细信息",
    responses={
        200: {"description": "模板详情"},
        404: {"model": ErrorResponse, "description": "模板不存在"},
    }
)
async def get_template_detail(table_type: str):
    """
    获取指定模板的详细信息
    """
    generator = get_generator()
    template_info = generator.get_template_info(table_type)
    
    if not template_info:
        raise HTTPException(
            status_code=404,
            detail=f"模板 '{table_type}' 不存在"
        )
    
    return TableTemplateInfo(**template_info)


@router.post(
    "/export",
    summary="导出表格",
    description="将表格导出为 CSV 或 Excel 格式",
    responses={
        200: {
            "description": "表格文件下载",
            "content": {
                "text/csv": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
            },
        },
        400: {"model": ErrorResponse, "description": "参数错误"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    }
)
async def export_table(request: TableExportRequest):
    """
    导出表格为 CSV 或 Excel 格式
    """
    try:
        generator = get_generator()
        
        # 生成导出文件
        result = await generator.export_table(
            table_type=request.table_type,
            context=request.context,
            export_format=request.export_format
        )
        
        content = result["content"]
        filename = request.filename or result["filename"]
        
        # 返回文件流
        if request.export_format == ExportFormat.EXCEL:
            return StreamingResponse(
                iter([content]),
                media_type=result["content_type"],
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Length": str(result["file_size"]),
                }
            )
        else:
            return StreamingResponse(
                iter([content]),
                media_type=result["content_type"],
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Length": str(result["file_size"]),
                }
            )
            
    except ValueError as e:
        logger.warning(f"表格导出参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"表格导出失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"表格导出失败: {str(e)}")


@router.get(
    "/health",
    summary="健康检查",
    description="检查表格生成服务健康状态",
)
async def health_check():
    """
    健康检查
    """
    return {
        "status": "healthy",
        "service": "table-generator",
        "version": "0.4.0",
        "templates_count": len(get_generator().list_available_templates())
    }

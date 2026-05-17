"""
表格生成模块 - Pydantic 数据模型
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ExportFormat(str, Enum):
    """导出格式枚举"""
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"


class TableGenerateRequest(BaseModel):
    """表格生成请求"""
    description: str = Field(
        ...,
        description="自然语言描述，如'生成桥梁施工安全检查表'",
        min_length=1,
        max_length=500
    )
    table_type: str = Field(
        ...,
        description="表格类型，如 'safety_check', 'risk_assessment', 'rectification', 'work_permit'"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="上下文信息，如 {'project_type': 'bridge', 'location': 'xxx'}"
    )
    use_rag: bool = Field(
        default=True,
        description="是否使用 RAG 知识库增强上下文"
    )
    custom_headers: Optional[List[str]] = Field(
        default=None,
        description="自定义表头（用于自定义表格类型）"
    )
    row_count: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="期望的行数（用于自定义表格）"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "description": "生成桥梁施工安全检查表",
                "table_type": "safety_check",
                "context": {"project_type": "bridge"},
                "use_rag": True
            }
        }


class TableData(BaseModel):
    """表格数据结构"""
    headers: List[str] = Field(..., description="表头列表")
    rows: List[List[Any]] = Field(..., description="行数据列表")
    
    def to_dict(self) -> Dict[str, Any]:
        return {"headers": self.headers, "rows": self.rows}
    
    def to_csv_string(self) -> str:
        """转换为 CSV 格式字符串"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self.headers)
        writer.writerows(self.rows)
        return output.getvalue()
    
    def to_excel_bytes(self) -> bytes:
        """转换为 Excel 格式字节"""
        import io
        from openpyxl import Workbook
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Table"
        
        # 写入表头
        ws.append(self.headers)
        
        # 写入数据行
        for row in self.rows:
            ws.append(row)
        
        # 保存到字节流
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()


class TableMetadata(BaseModel):
    """表格元数据"""
    type: str = Field(..., description="表格类型")
    template_name: str = Field(..., description="模板名称")
    row_count: int = Field(..., description="数据行数")
    column_count: int = Field(..., description="列数")
    generated_at: str = Field(..., description="生成时间")
    rag_enhanced: bool = Field(default=False, description="是否使用了RAG增强")
    rag_context: Optional[str] = Field(default=None, description="RAG补充的上下文")


class TableGenerateResponse(BaseModel):
    """表格生成响应"""
    success: bool = Field(..., description="是否成功")
    table: TableData = Field(..., description="表格数据")
    metadata: TableMetadata = Field(..., description="元数据")
    rag_answer: Optional[str] = Field(default=None, description="RAG检索结果（用于参考）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "table": {
                    "headers": ["序号", "检查项目", "检查内容", "标准要求", "检查结果", "整改要求", "检查人", "检查日期"],
                    "rows": [
                        [1, "高空作业安全", "检查高空作业人员是否正确佩戴安全带", "JGJ80-2016", "合格", "", "张三", "2024-01-15"]
                    ]
                },
                "metadata": {
                    "type": "safety_check",
                    "template_name": "安全检查表",
                    "row_count": 10,
                    "column_count": 8,
                    "generated_at": "2024-01-15T10:30:00",
                    "rag_enhanced": True
                }
            }
        }


class TableTemplateInfo(BaseModel):
    """模板信息"""
    template_id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称（中文）")
    name_en: str = Field(..., description="模板名称（英文）")
    description: str = Field(..., description="模板描述")
    headers: List[str] = Field(..., description="表头")
    required_context_keys: List[str] = Field(..., description="必需的上下文字段")
    category: str = Field(..., description="分类")


class TableTemplateListResponse(BaseModel):
    """模板列表响应"""
    success: bool = Field(default=True)
    templates: List[TableTemplateInfo] = Field(..., description="模板列表")
    total: int = Field(..., description="模板总数")


class TableExportRequest(BaseModel):
    """表格导出请求"""
    table_type: str = Field(..., description="表格类型")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文")
    export_format: ExportFormat = Field(default=ExportFormat.CSV, description="导出格式")
    filename: Optional[str] = Field(default=None, description="自定义文件名")


class TableExportResponse(BaseModel):
    """表格导出响应"""
    success: bool = Field(..., description="是否成功")
    filename: str = Field(..., description="文件名")
    content_type: str = Field(..., description="内容类型")
    file_size: int = Field(..., description="文件大小（字节）")
    download_url: Optional[str] = Field(default=None, description="下载链接（如果有）")


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(default=False)
    error_code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误信息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="详细信息")

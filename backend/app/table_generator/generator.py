"""
表格生成核心模块
Table Generator - Core Logic for Water Construction Safety System

提供基于 RAG 知识库的智能表格生成能力。
支持多种表格类型：安全检查表、风险评估矩阵、隐患整改记录表、特种作业许可证等。
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx

from .templates import TABLE_TEMPLATES, get_template, TableTemplate
from .schemas import (
    TableData,
    TableMetadata,
    TableGenerateResponse,
    ExportFormat,
)

logger = logging.getLogger(__name__)


class TableGenerator:
    """
    表格生成器
    
    输入自然语言描述，生成结构化表格。
    支持：
    1. 安全检查表生成
    2. 风险评估矩阵
    3. 隐患整改记录表
    4. 自定义表格
    
    特性：
    - RAG 知识库增强：自动从知识库检索相关规范和标准
    - 多模板支持：内置多种水利工程专用表格模板
    - 上下文感知：根据项目类型动态调整表格内容
    - 灵活扩展：支持自定义表头和行数
    """
    
    def __init__(
        self,
        coordinator_url: str = "http://ai-coordinator:8084",
        knowledge_url: str = "http://knowledge-base:8085",
        timeout: float = 30.0
    ):
        """
        初始化表格生成器
        
        Args:
            coordinator_url: AI 协调器服务地址
            knowledge_url: 知识库服务地址
            timeout: 请求超时时间（秒）
        """
        self.coordinator_url = coordinator_url
        self.knowledge_url = knowledge_url
        self.timeout = timeout
        self._templates = TABLE_TEMPLATES
    
    async def generate(
        self,
        description: str,
        table_type: str,
        context: Optional[Dict[str, Any]] = None,
        use_rag: bool = True,
        custom_headers: Optional[List[str]] = None,
        row_count: Optional[int] = None
    ) -> TableGenerateResponse:
        """
        生成表格
        
        Args:
            description: 自然语言描述，如"生成桥梁施工安全检查表"
            table_type: 表格类型，如 'safety_check', 'risk_assessment' 等
            context: 上下文信息，如 {'project_type': 'bridge'}
            use_rag: 是否使用 RAG 增强
            custom_headers: 自定义表头（用于自定义表格）
            row_count: 期望的行数（用于自定义表格）
            
        Returns:
            TableGenerateResponse: 包含表格数据和元数据的响应对象
        """
        start_time = datetime.now()
        context = context or {}
        rag_answer: Optional[str] = None
        
        try:
            # 1. 验证表格类型
            template = self._get_template_or_raise(table_type)
            
            # 2. RAG 增强上下文（如果启用）
            rag_enhanced = False
            if use_rag:
                try:
                    rag_answer = await self._enrich_context(description)
                    if rag_answer:
                        rag_enhanced = True
                        logger.info(f"RAG增强成功，获取到上下文: {rag_answer[:100]}...")
                except Exception as e:
                    logger.warning(f"RAG增强失败，继续使用基础生成: {e}")
            
            # 3. 生成表格数据
            table_data = await self._generate_table_data(
                template=template,
                context=context,
                custom_headers=custom_headers,
                row_count=row_count,
                rag_context=rag_answer if rag_enhanced else None
            )
            
            # 4. 构建元数据
            metadata = TableMetadata(
                type=table_type,
                template_name=template.name,
                row_count=len(table_data.rows),
                column_count=len(table_data.headers),
                generated_at=datetime.now().isoformat(),
                rag_enhanced=rag_enhanced,
                rag_context=rag_answer[:200] if rag_answer and rag_enhanced else None
            )
            
            # 5. 构建响应
            response = TableGenerateResponse(
                success=True,
                table=table_data,
                metadata=metadata,
                rag_answer=rag_answer
            )
            
            logger.info(
                f"表格生成成功: type={table_type}, rows={len(table_data.rows)}, "
                f"rag_enhanced={rag_enhanced}, elapsed={(datetime.now()-start_time).total_seconds():.2f}s"
            )
            
            return response
            
        except ValueError as e:
            logger.error(f"表格生成参数错误: {e}")
            raise
        except Exception as e:
            logger.error(f"表格生成失败: {e}", exc_info=True)
            raise
    
    def _get_template_or_raise(self, table_type: str) -> TableTemplate:
        """获取模板或抛出异常"""
        template = get_template(table_type)
        if not template:
            available = list(self._templates.keys())
            raise ValueError(
                f"未知的表格类型: '{table_type}'。"
                f"可用类型: {available}"
            )
        return template
    
    async def _enrich_context(self, description: str) -> str:
        """
        调用 RAG 知识库 API 增强上下文
        
        从水利工程安全规范知识库中检索与描述相关的条文和标准，
        用于生成更准确、更符合规范的表格内容。
        
        Args:
            description: 自然语言描述
            
        Returns:
            str: RAG 检索到的相关上下文内容
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # 调用知识库 RAG API
                resp = await client.post(
                    f"{self.knowledge_url}/query",
                    json={
                        "question": description,
                        "top_k": 3,
                        "collection": "safety_regulations"
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    return result.get("answer", "")
                else:
                    logger.warning(f"RAG API 返回错误状态: {resp.status_code}")
                    return ""
                    
            except httpx.ConnectError:
                logger.warning(f"无法连接到知识库服务: {self.knowledge_url}")
                return ""
            except httpx.TimeoutException:
                logger.warning("RAG API 请求超时")
                return ""
            except Exception as e:
                logger.error(f"RAG API 调用异常: {e}")
                return ""
    
    async def _generate_table_data(
        self,
        template: TableTemplate,
        context: Dict[str, Any],
        custom_headers: Optional[List[str]] = None,
        row_count: Optional[int] = None,
        rag_context: Optional[str] = None
    ) -> TableData:
        """
        生成表格数据
        
        Args:
            template: 表格模板
            context: 上下文信息
            custom_headers: 自定义表头
            row_count: 期望的行数
            rag_context: RAG 增强的上下文
            
        Returns:
            TableData: 表格数据对象
        """
        # 确定表头
        if custom_headers:
            headers = custom_headers
        else:
            headers = template.headers.copy()
        
        # 生成行数据
        if template.row_generator:
            rows = template.row_generator(context)
            # 如果指定了行数且需要扩展
            if row_count and len(rows) < row_count:
                rows = self._expand_rows(rows, row_count, headers, template.template_id)
        elif row_count:
            rows = self._generate_empty_rows(row_count, headers)
        else:
            rows = [["" for _ in headers]]
        
        return TableData(headers=headers, rows=rows)
    
    def _expand_rows(
        self,
        base_rows: List[List[Any]],
        target_count: int,
        headers: List[str],
        template_id: str
    ) -> List[List[Any]]:
        """
        扩展行数据至目标数量
        
        当基础行数不足时，根据模板类型补充合理的行数据。
        
        Args:
            base_rows: 基础行数据
            target_count: 目标行数
            headers: 表头
            template_id: 模板ID
            
        Returns:
            扩展后的行数据
        """
        rows = base_rows.copy()
        current_count = len(rows)
        
        if current_count >= target_count:
            return rows[:target_count]
        
        # 根据模板类型补充数据
        if template_id == "safety_check":
            supplement = self._generate_supplement_safety_check(
                current_count, target_count, headers
            )
        elif template_id == "risk_assessment":
            supplement = self._generate_supplement_risk_assessment(
                current_count, target_count, headers
            )
        else:
            supplement = self._generate_empty_rows(
                target_count - current_count, headers
            )
        
        rows.extend(supplement)
        return rows
    
    def _generate_supplement_safety_check(
        self,
        start_idx: int,
        count: int,
        headers: List[str]
    ) -> List[List[Any]]:
        """生成安全检查表的补充行"""
        today = datetime.now().strftime("%Y-%m-%d")
        supplement_items = [
            ("施工机具", "检查机具安全防护装置", "机械设备安全规程"),
            ("安全标志", "检查安全标志牌设置", "安全标志设置规范"),
            ("宿舍安全", "检查临时宿舍用电安全", "施工现场临时设施规范"),
            ("食堂卫生", "检查食堂卫生许可证", "食品卫生管理规定"),
            ("应急通道", "检查疏散通道畅通", "消防安全管理规范"),
        ]
        
        rows = []
        for i, (project, content, standard) in enumerate(supplement_items):
            if len(rows) >= count:
                break
            rows.append([
                start_idx + i + 1,
                project,
                content,
                standard,
                "合格/不合格",
                "",
                "",
                today,
            ])
        
        return rows
    
    def _generate_supplement_risk_assessment(
        self,
        start_idx: int,
        count: int,
        headers: List[str]
    ) -> List[List[Any]]:
        """生成风险评估矩阵的补充行"""
        supplement_items = [
            ("交通事故", "施工车辆运输", 2, 3, "施工车辆管理", "限速警示"),
            ("环境事故", "泥浆外溢", 2, 3, "环境保护规范", "沉淀处理"),
            ("职业病", "粉尘噪音", 3, 3, "职业健康规范", "防护用品"),
        ]
        
        rows = []
        for i, (point, desc, L, S, std, measure) in enumerate(supplement_items):
            if len(rows) >= count:
                break
            R = L * S
            if R >= 15:
                level = "重大风险"
            elif R >= 9:
                level = "较大风险"
            elif R >= 4:
                level = "一般风险"
            else:
                level = "低风险"
            
            rows.append([point, desc, L, S, R, level, measure])
        
        return rows
    
    def _generate_empty_rows(self, count: int, headers: List[str]) -> List[List[Any]]:
        """生成空白行"""
        return [[""] * len(headers) for _ in range(count)]
    
    async def export_table(
        self,
        table_type: str,
        context: Optional[Dict[str, Any]] = None,
        export_format: ExportFormat = ExportFormat.CSV
    ) -> Dict[str, Any]:
        """
        导出表格为指定格式
        
        Args:
            table_type: 表格类型
            context: 上下文信息
            export_format: 导出格式
            
        Returns:
            包含文件内容和元信息的字典
        """
        # 生成表格
        response = await self.generate(
            description=f"生成 {table_type} 表格",
            table_type=table_type,
            context=context,
            use_rag=False
        )
        
        table_data = response.table
        template = get_template(table_type)
        
        # 根据格式生成内容
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        template_name = template.name if template else table_type
        
        if export_format == ExportFormat.CSV:
            content = table_data.to_csv_string()
            content_type = "text/csv"
            extension = "csv"
        elif export_format == ExportFormat.EXCEL:
            content = table_data.to_excel_bytes()
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            extension = "xlsx"
        else:  # JSON
            content = json.dumps(table_data.to_dict(), ensure_ascii=False, indent=2)
            content_type = "application/json"
            extension = "json"
        
        filename = f"{template_name}_{timestamp}.{extension}"
        
        return {
            "content": content,
            "filename": filename,
            "content_type": content_type,
            "file_size": len(content) if isinstance(content, str) else len(content)
        }
    
    def list_available_templates(self) -> List[Dict[str, Any]]:
        """
        列出所有可用的表格模板
        
        Returns:
            模板信息列表
        """
        from .templates import list_templates
        return list_templates()
    
    def get_template_info(self, table_type: str) -> Optional[Dict[str, Any]]:
        """
        获取指定模板的详细信息
        
        Args:
            table_type: 表格类型
            
        Returns:
            模板详细信息字典，不存在则返回 None
        """
        template = get_template(table_type)
        if template:
            return template.to_dict()
        return None

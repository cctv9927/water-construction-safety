"""
水利工地安全监管系统 - 智能表格生成模块
Table Generator Module for Water Construction Safety System

提供基于 RAG 知识库的智能表格生成能力，
支持安全检查表、风险评估矩阵、隐患整改记录表等多种表格类型。
"""

from .generator import TableGenerator
from .schemas import (
    TableGenerateRequest,
    TableGenerateResponse,
    TableTemplate,
    TableExportRequest,
)
from .templates import TABLE_TEMPLATES, get_template, list_templates

__all__ = [
    "TableGenerator",
    "TableGenerateRequest",
    "TableGenerateResponse",
    "TableTemplate",
    "TableExportRequest",
    "TABLE_TEMPLATES",
    "get_template",
    "list_templates",
]

__version__ = "0.4.0"

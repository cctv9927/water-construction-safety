"""
表格生成模块集成测试

测试覆盖：
- 表格生成 → 返回 JSON 表结构
- 列出可用模板
- 获取模板详情
- 导出表格（CSV/Excel）
- 健康检查
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


@pytest.fixture
def mock_generator():
    """Mock 表格生成器"""
    mock_gen = MagicMock()
    mock_gen.generate = AsyncMock()
    mock_gen.list_available_templates = MagicMock(return_value=[
        {"id": "safety_check", "name": "安全检查表", "category": "safety", "headers": ["项目", "标准", "结果"]},
        {"id": "risk_assessment", "name": "风险评估矩阵", "category": "risk", "headers": ["风险项", "等级", "措施"]},
        {"id": "rectification", "name": "隐患整改记录表", "category": "safety", "headers": ["隐患描述", "整改人", "期限"]},
        {"id": "work_permit", "name": "特种作业许可证", "category": "permit", "headers": ["作业内容", "审批人", "有效期"]},
    ])
    mock_gen.get_template_info = MagicMock(return_value={
        "id": "safety_check",
        "name": "安全检查表",
        "category": "safety",
        "headers": ["序号", "检查项目", "检查标准", "检查方法", "判定"]
    })
    mock_gen.export_table = AsyncMock()
    return mock_gen


@pytest.mark.asyncio
async def test_generate_safety_check_table(client, auth_headers, mock_generator):
    """测试生成安全检查表"""
    mock_response = MagicMock()
    mock_response.table_data = {
        "headers": ["序号", "检查项目", "检查标准", "检查方法", "判定"],
        "rows": [
            ["1", "临边防护", "防护栏高度≥1.2m", "尺量", "合格/不合格"],
            ["2", "用电安全", "三级配电两级保护", "检查配电箱", "合格/不合格"],
            ["3", "消防安全", "消防通道畅通", "现场检查", "合格/不合格"],
            ["4", "高空作业", "安全带高挂低用", "检查安全带", "合格/不合格"],
            ["5", "基坑支护", "支护结构完整", "观察检查", "合格/不合格"],
        ]
    }
    mock_response.generated_at = datetime.now()
    mock_response.table_type = "safety_check"
    mock_response.title = "水利工程安全检查表"
    mock_generator.generate.return_value = mock_response

    with patch("app.table_generator.router.get_generator", return_value=mock_generator):
        response = await client.post(
            "/api/table/generate",
            json={
                "description": "水利工程日常安全检查",
                "table_type": "safety_check",
                "use_rag": True,
                "row_count": 10
            },
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "table_data" in data
    assert "headers" in data["table_data"]
    assert "rows" in data["table_data"]


@pytest.mark.asyncio
async def test_generate_risk_assessment_table(client, auth_headers, mock_generator):
    """测试生成风险评估矩阵表"""
    mock_response = MagicMock()
    mock_response.table_data = {
        "headers": ["风险项", "可能性", "严重性", "风险等级", "控制措施"],
        "rows": [
            ["基坑坍塌", "中", "高", "重大风险", "加强支护监测"],
            ["高处坠落", "低", "高", "中等风险", "系好安全带"],
            ["机械伤害", "中", "中", "一般风险", "规范操作"],
        ]
    }
    mock_response.generated_at = datetime.now()
    mock_response.table_type = "risk_assessment"
    mock_response.title = "风险评估矩阵"
    mock_generator.generate.return_value = mock_response

    with patch("app.table_generator.router.get_generator", return_value=mock_generator):
        response = await client.post(
            "/api/table/generate",
            json={
                "description": "大坝施工风险评估",
                "table_type": "risk_assessment",
                "use_rag": False
            },
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["table_data"]["headers"] == ["风险项", "可能性", "严重性", "风险等级", "控制措施"]


@pytest.mark.asyncio
async def test_generate_table_with_rag_enhancement(client, auth_headers, mock_generator):
    """测试启用 RAG 增强的表格生成"""
    mock_response = MagicMock()
    mock_response.table_data = {"headers": [], "rows": []}
    mock_response.generated_at = datetime.now()
    mock_response.table_type = "rectification"
    mock_response.title = "隐患整改表"
    mock_generator.generate.return_value = mock_response

    with patch("app.table_generator.router.get_generator", return_value=mock_generator):
        response = await client.post(
            "/api/table/generate",
            json={
                "description": "基坑隐患整改记录",
                "table_type": "rectification",
                "use_rag": True,
                "context": {"project_type": "dam"}
            },
            headers=auth_headers
        )
    
    assert response.status_code == 200
    mock_generator.generate.assert_called_once()
    call_kwargs = mock_generator.generate.call_args[1]
    assert call_kwargs["use_rag"] is True


@pytest.mark.asyncio
async def test_generate_table_with_custom_headers(client, auth_headers, mock_generator):
    """测试带自定义表头的表格生成"""
    mock_response = MagicMock()
    mock_response.table_data = {"headers": [], "rows": []}
    mock_response.generated_at = datetime.now()
    mock_response.table_type = "custom"
    mock_response.title = "自定义表格"
    mock_generator.generate.return_value = mock_response

    with patch("app.table_generator.router.get_generator", return_value=mock_generator):
        response = await client.post(
            "/api/table/generate",
            json={
                "description": "自定义格式的检查表",
                "table_type": "safety_check",
                "custom_headers": ["序号", "检查项", "结果", "备注"]
            },
            headers=auth_headers
        )
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_all_templates(client, mock_generator):
    """测试列出所有可用模板"""
    with patch("app.table_generator.router.get_generator", return_value=mock_generator):
        response = await client.get("/api/table/templates")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total"] == 4
    assert len(data["templates"]) == 4


@pytest.mark.asyncio
async def test_list_templates_by_category(client, mock_generator):
    """测试按分类筛选模板"""
    with patch("app.table_generator.router.get_generator", return_value=mock_generator):
        response = await client.get("/api/table/templates?category=safety")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # 至少应该返回 safety 分类的模板
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_template_detail(client, mock_generator):
    """测试获取模板详情"""
    with patch("app.table_generator.router.get_generator", return_value=mock_generator):
        response = await client.get("/api/table/templates/safety_check")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "safety_check"
    assert "headers" in data


@pytest.mark.asyncio
async def test_get_template_detail_not_found(client, mock_generator):
    """测试获取不存在的模板 → 404"""
    mock_generator.get_template_info.return_value = None

    with patch("app.table_generator.router.get_generator", return_value=mock_generator):
        response = await client.get("/api/table/templates/nonexistent_template")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_table_csv(client, auth_headers, mock_generator):
    """测试导出表格为 CSV 格式"""
    mock_result = {
        "content": "序号,检查项目,判定\n1,临边防护,合格",
        "filename": "safety_check.csv",
        "content_type": "text/csv",
        "file_size": 50
    }
    mock_generator.export_table.return_value = mock_result

    with patch("app.table_generator.router.get_generator", return_value=mock_generator):
        response = await client.post(
            "/api/table/export",
            json={
                "table_type": "safety_check",
                "context": {},
                "export_format": "csv"
            },
            headers=auth_headers
        )
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_export_table_excel(client, auth_headers, mock_generator):
    """测试导出表格为 Excel 格式"""
    mock_result = {
        "content": b"PK\x03\x04...",
        "filename": "safety_check.xlsx",
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "file_size": 2048
    }
    mock_generator.export_table.return_value = mock_result

    with patch("app.table_generator.router.get_generator", return_value=mock_generator):
        response = await client.post(
            "/api/table/export",
            json={
                "table_type": "safety_check",
                "export_format": "excel"
            },
            headers=auth_headers
        )
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_table_generator_health_check(client):
    """测试表格生成服务健康检查"""
    response = await client.get("/api/table/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


@pytest.mark.asyncio
async def test_generate_table_unauthorized(client):
    """测试无认证生成表格 → 401"""
    response = await client.post(
        "/api/table/generate",
        json={"description": "test", "table_type": "safety_check"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_table_invalid_type(client, auth_headers):
    """测试无效表格类型"""
    mock_gen = MagicMock()
    mock_gen.generate.side_effect = ValueError("不支持的表格类型: invalid_type")

    with patch("app.table_generator.router.get_generator", return_value=mock_gen):
        response = await client.post(
            "/api/table/generate",
            json={"description": "test", "table_type": "invalid_type"},
            headers=auth_headers
        )
    
    assert response.status_code in [400, 500]

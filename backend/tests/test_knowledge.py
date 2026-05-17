"""
知识库模块集成测试

测试覆盖：
- RAG 问答 → 返回 answer + sources
- 初始化种子数据 → 200
- 表格生成 → 返回 JSON 表结构
- 添加文档
- 知识库统计
- 健康检查
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


@pytest.mark.asyncio
async def test_knowledge_query_success(client, auth_headers):
    """测试 RAG 问答 → 返回 answer + sources"""
    mock_result = {
        "answer": "根据水利工程施工安全规范，高空作业应采取以下防护措施...",
        "sources": [
            {"content": "高空作业必须系好安全带...", "score": 0.95, "source": "GB 3608-2008"},
            {"content": "安全带应高挂低用...", "score": 0.88, "source": "SL 721-2010"}
        ],
        "generated_at": datetime.now().isoformat()
    }

    def get_vs():
        mock_vs = MagicMock()
        mock_vs.get_stats.return_value = {"total_documents": 10, "total_chunks": 50}
        return mock_vs

    def get_pipeline():
        mock_pipe = MagicMock()
        mock_pipe.query.return_value = mock_result
        return mock_pipe

    with patch("app.knowledge.router.get_kg_pipeline", get_pipeline), \
         patch("app.knowledge.router.get_vector_store", get_vs):
        response = await client.post(
            "/api/knowledge/query",
            json={"question": "高空作业有哪些安全要求？", "top_k": 5},
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert "generated_at" in data
    assert len(data["sources"]) == 2


@pytest.mark.asyncio
async def test_knowledge_query_with_category_filter(client, auth_headers):
    """测试带分类过滤的 RAG 问答"""
    mock_result = {
        "answer": "关于用电安全...",
        "sources": [{"content": "用电安全规范...", "score": 0.92, "source": "JGJ 46-2005"}],
        "generated_at": datetime.now().isoformat()
    }

    def get_pipeline():
        mock_pipe = MagicMock()
        mock_pipe.query.return_value = mock_result
        return mock_pipe

    with patch("app.knowledge.router.get_kg_pipeline", get_pipeline):
        response = await client.post(
            "/api/knowledge/query",
            json={"question": "施工现场临时用电规范？", "top_k": 3, "category": "用电安全"},
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data


@pytest.mark.asyncio
async def test_knowledge_seed_success(client, auth_headers):
    """测试初始化种子数据 → 200"""
    with patch("app.knowledge.router.seed_all_knowledge", AsyncMock()):
        response = await client.post(
            "/api/knowledge/seed",
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_add_document_success(client, auth_headers):
    """测试添加文档到知识库"""
    mock_chunks = [MagicMock(id="chunk_001")]
    mock_vs = MagicMock()
    mock_vs.upsert.return_value = True

    with patch("app.knowledge.router.get_vector_store", return_value=mock_vs), \
         patch("app.knowledge.router.DocumentLoader") as mock_loader_class, \
         patch("app.knowledge.router.load_and_chunk", return_value=mock_chunks):
        
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        
        response = await client.post(
            "/api/knowledge/add",
            json={
                "content": "水利工程施工现场用电安全规范：临时用电设备必须接地保护...",
                "title": "临时用电安全规范",
                "source": "JGJ 46-2005",
                "category": "用电安全"
            },
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["chunks_count"] == 1


@pytest.mark.asyncio
async def test_add_document_empty_content(client, auth_headers):
    """测试添加空文档"""
    mock_vs = MagicMock()

    with patch("app.knowledge.router.get_vector_store", return_value=mock_vs), \
         patch("app.knowledge.router.load_and_chunk", return_value=[]):
        response = await client.post(
            "/api/knowledge/add",
            json={
                "content": "",
                "title": "空文档",
                "source": "test",
                "category": "test"
            },
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["chunks_count"] == 0


@pytest.mark.asyncio
async def test_table_generation_success(client, auth_headers):
    """测试表格生成 → 返回 JSON 表结构"""
    mock_table_data = {
        "headers": ["序号", "检查项目", "检查标准", "检查方法", "判定"],
        "rows": [
            [1, "临边防护", "防护栏高度≥1.2m", "目测+尺量", "合格/不合格"],
            [2, "用电安全", "三级配电两级保护", "检查配电箱", "合格/不合格"],
            [3, "消防安全", "消防器材完好有效", "检查灭火器", "合格/不合格"],
        ]
    }
    mock_result = {
        "table_data": mock_table_data,
        "generated_at": datetime.now().isoformat()
    }

    def get_pipeline():
        mock_pipe = MagicMock()
        mock_pipe.query_table.return_value = mock_result
        return mock_pipe

    with patch("app.knowledge.router.get_kg_pipeline", get_pipeline):
        response = await client.post(
            "/api/knowledge/table",
            json={"topic": "水利工程安全检查项目", "rows": 10},
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "table_data" in data
    assert "headers" in data["table_data"]
    assert "rows" in data["table_data"]


@pytest.mark.asyncio
async def test_table_generation_custom_rows(client, auth_headers):
    """测试自定义行数的表格生成"""
    mock_result = {
        "table_data": {"headers": [], "rows": []},
        "generated_at": datetime.now().isoformat()
    }

    def get_pipeline():
        mock_pipe = MagicMock()
        mock_pipe.query_table.return_value = mock_result
        return mock_pipe

    with patch("app.knowledge.router.get_kg_pipeline", get_pipeline):
        response = await client.post(
            "/api/knowledge/table",
            json={"topic": "风险评估", "rows": 20},
            headers=auth_headers
        )
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_knowledge_stats(client, auth_headers):
    """测试获取知识库统计"""
    def get_vs():
        mock_vs = MagicMock()
        mock_vs.get_stats.return_value = {
            "total_documents": 156,
            "total_chunks": 1500
        }
        return mock_vs

    with patch("app.knowledge.router.get_vector_store", get_vs):
        response = await client.get(
            "/api/knowledge/stats",
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "total_chunks" in data


@pytest.mark.asyncio
async def test_knowledge_health_check(client):
    """测试知识库服务健康检查"""
    def get_vs():
        mock_vs = MagicMock()
        mock_vs.get_stats.return_value = {"total_chunks": 100}
        return mock_vs

    with patch("app.knowledge.router.get_vector_store", get_vs):
        response = await client.get("/api/knowledge/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_case_analyze(client, auth_headers):
    """测试事故案例分析"""
    def get_pipeline():
        mock_pipe = MagicMock()
        mock_pipe.query_case_analysis.return_value = "分析结果：这是一起因临边防护不到位导致的高空坠落事故..."
        return mock_pipe

    with patch("app.knowledge.router.get_kg_pipeline", get_pipeline):
        response = await client.post(
            "/api/knowledge/case/analyze",
            params={
                "case_description": "某工地发生一起高空坠落事故",
                "background": "当日风力6级，作业高度约15米"
            },
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "analysis" in data
    assert "generated_at" in data


@pytest.mark.asyncio
async def test_clear_knowledge(client, auth_headers):
    """测试清空知识库（管理员接口）"""
    response = await client.delete(
        "/api/knowledge/clear",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

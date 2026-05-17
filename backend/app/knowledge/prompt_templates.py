"""Prompt 模板"""

# 通用问答 Prompt
RAG_QA_PROMPT = """你是水利工地安全监管专家知识库的助手。根据以下参考资料，回答用户的问题。

参考资料：
{contexts}

问题：{question}

要求：
1. 基于参考资料给出准确、专业的回答
2. 如果参考资料不足以回答问题，请明确说明
3. 回答要条理清晰，必要时可分点说明
4. 涉及安全规范的内容，请注明参考来源
5. 回答用中文

回答："""

# 带分类的问答 Prompt
RAG_QA_WITH_CATEGORY_PROMPT = """你是水利工地安全监管专家知识库的助手。以下是关于「{category}」分类的参考资料：

参考资料：
{contexts}

问题：{question}

请基于以上参考资料给出专业、准确的回答，并注明参考来源。回答用中文。"""

# 表格生成 Prompt
TABLE_GENERATION_PROMPT = """你是水利工地安全监管专家。请根据以下要求生成结构化的安全检查表格数据。

主题：{topic}

要求：
1. 生成一个 JSON 格式的表格，包含表头和行数据
2. 表头应简洁明确
3. 行数据应覆盖主题的关键检查项
4. 每行数据要具体、可操作

请严格按照以下 JSON 格式输出，不要包含任何其他内容：
{{
    "title": "表格标题",
    "headers": ["表头1", "表头2", "表头3", ...],
    "rows": [
        ["行1列1", "行1列2", "行1列3", ...],
        ["行2列1", "行2列2", "行2列3", ...],
        ...
    ]
}}

JSON 输出："""

# 案例分析 Prompt
CASE_ANALYSIS_PROMPT = """你是水利工地安全管理专家。请分析以下事故案例：

事故描述：
{case_description}

背景信息：
{background}

分析要求：
1. 事故原因分析（直接原因、间接原因）
2. 违反的安全规范
3. 应采取的预防措施
4. 类似事故的警示要点

请给出专业、详细的分析报告。"""

# 规范查询 Prompt
REGULATION_QUERY_PROMPT = """你是水利工程安全规范专家。请根据以下问题查找相关安全规范：

问题：{question}

相关规范：
{regulations}

请指出问题涉及的具体规范条款，并解释其要求。"""

# 安全检查 Prompt
SAFETY_CHECK_PROMPT = """你是水利工地安全检查专家。请根据以下场景给出安全检查要点：

检查场景：{scene}
相关规范：{regulations}

请列出主要检查项目和合格标准。"""

# 应急处置 Prompt
EMERGENCY_RESPONSE_PROMPT = """你是水利工地应急处置专家。请针对以下紧急情况给出处置建议：

紧急情况：{situation}
当前状态：{current_status}

请按以下格式回答：
1. 立即行动（必须立即执行的措施）
2. 报告程序（应报告的对象和内容）
3. 后续处理（后续应采取的措施）
4. 预防建议（避免再次发生的建议）"""

# 格式化上下文（将多个文档格式化为上下文字符串）
def format_contexts(contexts: list, max_length: int = 2000) -> str:
    """格式化上下文列表为字符串"""
    formatted = []
    total_len = 0

    for ctx in contexts:
        content = ctx.get("content", "")
        source = ctx.get("source", "未知来源")
        category = ctx.get("category", "")
        title = ctx.get("title", "")

        # 添加来源信息
        source_str = f"【来源：{source}】"
        if category:
            source_str = f"【{category} | {source}】"

        block = f"{title}\n{source_str}\n{content}\n"

        if total_len + len(block) > max_length:
            # 截断超长内容
            remaining = max_length - total_len - 50
            if remaining > 100:
                block = block[:remaining] + "...(内容截断)"
            else:
                break

        formatted.append(block)
        total_len += len(block)

    return "\n---\n".join(formatted)


# 解析 LLM 输出（提取 JSON）
def extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON"""
    import json
    import re

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 块
    json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    matches = re.findall(json_pattern, text)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # 尝试提取 { ... } 块
    brace_pattern = r'\{[\s\S]*\}'
    matches = re.findall(brace_pattern, text)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    return {}

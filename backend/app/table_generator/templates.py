"""
内置表格模板定义
Built-in Table Templates for Water Construction Safety
"""

from typing import Dict, List, Any, Callable, Optional
from datetime import datetime


# ============ 表格模板类型定义 ============

class TableTemplate:
    """表格模板定义"""
    
    def __init__(
        self,
        template_id: str,
        name: str,
        name_en: str,
        description: str,
        headers: List[str],
        row_generator: Optional[Callable] = None,
        required_context_keys: Optional[List[str]] = None,
        category: str = "safety"
    ):
        self.template_id = template_id
        self.name = name
        self.name_en = name_en
        self.description = description
        self.headers = headers
        self.row_generator = row_generator
        self.required_context_keys = required_context_keys or []
        self.category = category
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "name_en": self.name_en,
            "description": self.description,
            "headers": self.headers,
            "required_context_keys": self.required_context_keys,
            "category": self.category,
        }
    
    def generate_rows(self, context: Optional[Dict] = None) -> List[List[Any]]:
        """根据上下文生成表格行数据"""
        if self.row_generator and context:
            return self.row_generator(context)
        # 默认返回空行
        return [["" for _ in self.headers]]


# ============ 行生成器函数 ============

def generate_safety_check_rows(context: Optional[Dict] = None) -> List[List[Any]]:
    """生成安全检查表行数据"""
    project_type = context.get("project_type", "general") if context else "general"
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 根据项目类型调整检查项
    safety_items = {
        "bridge": [
            ("高空作业安全", "检查高空作业人员是否正确佩戴安全带、安全帽", "JGJ80-2016"),
            ("脚手架安全", "检查脚手架搭设是否符合规范要求", "JGJ130-2011"),
            ("起重机械", "检查塔吊、吊车等起重设备是否定期检验", "GB6067.1-2010"),
            ("临时用电", "检查配电箱、开关箱设置及接地保护", "JGJ46-2005"),
            ("模板支撑", "检查模板支撑体系稳定性", "JGJ162-2008"),
            ("施工升降机", "检查升降机安全装置有效性", "GB10054-2005"),
            ("消防安全", "检查消防器材配置及通道畅通", "GB50720-2011"),
            ("临边防护", "检查桥梁临边、洞口防护措施", "JGJ80-2016"),
            ("水上作业", "检查救生衣、救生圈配置", "水上作业安全规程"),
            ("应急救援", "检查应急预案及救援物资", "安全生产法"),
        ],
        "dam": [
            ("基坑作业安全", "检查基坑支护及监测措施", "JGJ120-2012"),
            ("爆破作业安全", "检查爆破作业审批及警戒", "GB6722-2014"),
            ("高边坡作业", "检查边坡稳定及防护措施", "岩土工程勘察规范"),
            ("混凝土浇筑", "检查模板系统及浇筑工艺", "JGJ162-2008"),
            ("灌浆作业", "检查灌浆设备及施工质量", "水工建筑物灌浆施工规范"),
            ("度汛安全", "检查截流、度汛措施", "水利水电工程施工安全规范"),
            ("导流设施", "检查导流洞、围堰安全", "水利工程施工规范"),
            ("地质预报", "检查施工期地质预报系统", "工程地质勘察规范"),
        ],
        "tunnel": [
            ("隧道开挖安全", "检查开挖方法及支护措施", "TB10304-2020"),
            ("通风照明", "检查隧道通风及照明系统", "隧道施工安全规范"),
            ("排水系统", "检查排水设备及应急排水", "地下工程防水规范"),
            ("爆破作业", "检查爆破方案及防护措施", "GB6722-2014"),
            ("监控量测", "检查围岩变形监测", "TB10121-2007"),
            ("逃生通道", "检查应急逃生设施", "隧道施工安全规范"),
            ("有毒气体", "检查气体检测及通风", "矿山安全规程"),
            ("电力安全", "检查电缆敷设及保护", "施工现场临时用电规范"),
        ],
        "general": [
            ("人员资质", "检查特种作业人员持证情况", "安全生产法"),
            ("安全培训", "检查三级安全教育培训记录", "安全培训管理办法"),
            ("个人防护", "检查安全帽、安全带、防护鞋佩戴", "个体防护装备规范"),
            ("施工用电", "检查配电系统及漏电保护", "JGJ46-2005"),
            ("机械设备", "检查机械设备维护保养记录", "机械设备安全规程"),
            ("消防安全", "检查消防器材配置", "GB50720-2011"),
            ("临边洞口", "检查防护设施设置", "JGJ80-2016"),
            ("文明施工", "检查施工现场管理", "文明施工规范"),
        ],
    }
    
    items = safety_items.get(project_type, safety_items["general"])
    rows = []
    for idx, (project, content, standard) in enumerate(items, 1):
        rows.append([
            idx,          # 序号
            project,      # 检查项目
            content,      # 检查内容
            standard,     # 标准要求
            "合格/不合格",  # 检查结果
            "",           # 整改要求
            "",           # 检查人
            today,        # 检查日期
        ])
    return rows


def generate_risk_assessment_rows(context: Optional[Dict] = None) -> List[List[Any]]:
    """生成风险评估矩阵行数据"""
    project_type = context.get("project_type", "general") if context else "general"
    
    risk_items = {
        "bridge": [
            ("高处坠落", "桥梁墩柱、桥面施工", 4, 5, "高处作业规范", "必须使用安全带"),
            ("物体打击", "模板、钢筋吊装作业", 3, 4, "起重作业规范", "设置警戒区"),
            ("坍塌事故", "脚手架、模板支撑", 3, 5, "支撑体系规范", "严格验收程序"),
            ("机械伤害", "施工机械操作", 3, 3, "机械安全规程", "持证上岗"),
            ("触电事故", "临时用电", 2, 4, "用电安全规范", "三级配电两级保护"),
            ("水上溺水", "水中作业", 2, 5, "水上作业规范", "救生设备配备"),
        ],
        "dam": [
            ("边坡失稳", "高边坡开挖", 3, 5, "边坡工程技术规范", "监测预警系统"),
            ("基坑坍塌", "基坑开挖支护", 3, 5, "基坑支护规范", "信息化施工"),
            ("爆破伤害", "石方爆破", 2, 5, "爆破安全规程", "警戒疏散程序"),
            ("机械伤害", "大型设备作业", 3, 3, "机械安全规程", "专项施工方案"),
            ("淹溺事故", "导截流施工", 2, 5, "水上作业规范", "应急救援预案"),
            ("高处坠落", "大坝混凝土浇筑", 4, 4, "高处作业规范", "满堂脚手架"),
        ],
        "tunnel": [
            ("塌方冒顶", "隧道开挖", 3, 5, "隧道施工规范", "超前地质预报"),
            ("突泥涌水", "富水地段", 2, 5, "隧道防水规范", "注浆堵水措施"),
            ("瓦斯爆炸", "瓦斯隧道", 2, 5, "瓦斯隧道规范", "瓦斯监测通风"),
            ("机械伤害", "出渣运输", 3, 3, "机械安全规程", "限速警示"),
            ("触电伤害", "施工用电", 2, 4, "用电安全规范", "漏电保护"),
            ("火工品事故", "爆破作业", 2, 5, "爆破安全规程", "严格管控程序"),
        ],
        "general": [
            ("高处坠落", "高空作业", 4, 4, "高处作业规范", "安全带使用"),
            ("物体打击", "交叉作业", 3, 3, "安全防护规范", "防护棚设置"),
            ("机械伤害", "设备操作", 3, 3, "机械安全规程", "操作规程"),
            ("触电事故", "临时用电", 2, 4, "用电安全规范", "接地保护"),
            ("火灾事故", "易燃材料", 2, 4, "消防安全管理", "消防器材配置"),
            ("中毒窒息", "有限空间", 2, 5, "有限空间规范", "气体检测通风"),
        ],
    }
    
    items = risk_items.get(project_type, risk_items["general"])
    rows = []
    for risk_point, desc, L, S, standard, measure in items:
        R = L * S
        # 风险等级判定
        if R >= 15:
            level = "重大风险"
        elif R >= 9:
            level = "较大风险"
        elif R >= 4:
            level = "一般风险"
        else:
            level = "低风险"
        
        rows.append([
            risk_point,  # 风险点
            L,           # 可能性(L)
            S,           # 严重性(S)
            R,           # 风险值(R=L×S)
            level,       # 风险等级
            measure,     # 管控措施
        ])
    return rows


def generate_rectification_rows(context: Optional[Dict] = None) -> List[List[Any]]:
    """生成隐患整改记录表行数据"""
    return [
        ["隐患描述", "一般/重大", datetime.now().strftime("%Y-%m-%d %H:%M"), "", "", "待整改", ""],
    ]


def generate_work_permit_rows(context: Optional[Dict] = None) -> List[List[Any]]:
    """生成特种作业许可证行数据"""
    return [
        ["作业内容", "作业地点", datetime.now().strftime("%Y-%m-%d"), "", "", "", ""],
    ]


# ============ 模板注册表 ============

TABLE_TEMPLATES: Dict[str, TableTemplate] = {
    "safety_check": TableTemplate(
        template_id="safety_check",
        name="安全检查表",
        name_en="Safety Inspection Checklist",
        description="水利工程施工现场安全检查标准表格，适用于日常巡检、专项检查等场景",
        headers=["序号", "检查项目", "检查内容", "标准要求", "检查结果", "整改要求", "检查人", "检查日期"],
        row_generator=generate_safety_check_rows,
        required_context_keys=["project_type"],
        category="safety"
    ),
    
    "risk_assessment": TableTemplate(
        template_id="risk_assessment",
        name="风险评估矩阵",
        name_en="Risk Assessment Matrix",
        description="基于LEC法的风险评估矩阵，用于施工风险识别和分级管控",
        headers=["风险点", "风险描述", "可能性(L)", "严重性(S)", "风险值(R=L×S)", "风险等级", "管控措施"],
        row_generator=generate_risk_assessment_rows,
        required_context_keys=["project_type"],
        category="risk"
    ),
    
    "rectification": TableTemplate(
        template_id="rectification",
        name="隐患整改记录表",
        name_en="Hazard Rectification Record",
        description="安全隐患整改跟踪记录表，用于隐患发现、整改、验收全流程管理",
        headers=["隐患描述", "隐患等级", "发现时间", "整改措施", "整改期限", "整改状态", "验收结果"],
        row_generator=generate_rectification_rows,
        required_context_keys=[],
        category="safety"
    ),
    
    "work_permit": TableTemplate(
        template_id="work_permit",
        name="特种作业许可证",
        name_en="Special Work Permit",
        description="特种作业审批表格，包括动火作业、受限空间、高处作业等",
        headers=["作业内容", "作业地点", "作业时间", "作业人员", "安全员", "防护措施", "审批人"],
        row_generator=generate_work_permit_rows,
        required_context_keys=[],
        category="permit"
    ),
}


def get_template(template_id: str) -> Optional[TableTemplate]:
    """获取指定模板"""
    return TABLE_TEMPLATES.get(template_id)


def list_templates(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """列出所有可用模板"""
    templates = list(TABLE_TEMPLATES.values())
    if category:
        templates = [t for t in templates if t.category == category]
    return [t.to_dict() for t in templates]

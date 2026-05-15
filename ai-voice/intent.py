"""
意图识别模块
- 基于关键词的意图检测
- 支持多种水利工地安全相关意图
"""
import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """意图类型枚举"""
    ALERT_HELP = "alert_help"           # 紧急求助
    ALERT_FIRE = "alert_fire"           # 火灾报警
    ALERT_INJURY = "alert_injury"       # 人员伤亡
    ALERT_ENV = "alert_environment"     # 环境异常
    STATUS_QUERY = "status_query"       # 状态查询
    COMMAND_START = "command_start"     # 启动指令
    COMMAND_STOP = "command_stop"       # 停止指令
    COMMAND_EVACUATE = "command_evacuate"  # 疏散指令
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: IntentType
    confidence: float
    entities: Dict[str, Any]
    raw_text: str
    keywords_matched: List[str]


class KeywordIntentDetector:
    """基于关键词的意图检测器"""

    # 关键词配置
    KEYWORD_CONFIG = {
        IntentType.ALERT_HELP: {
            "keywords": ["救命", "救命啊", "帮助", "救我", "救命！", "来人", "快来"],
            "weight": 1.0,
        },
        IntentType.ALERT_FIRE: {
            "keywords": ["火", "着火", "起火", "火灾", "烧", "火警", "冒烟", "烟雾"],
            "weight": 0.9,
        },
        IntentType.ALERT_INJURY: {
            "keywords": ["受伤", "流血", "骨折", "事故", "伤亡", "晕倒", "倒下", "危险"],
            "weight": 0.9,
        },
        IntentType.ALERT_ENV: {
            "keywords": ["漏电", "漏水", "渗水", "坍塌", "滑坡", "有毒", "气体", "异味", "超标"],
            "weight": 0.8,
        },
        IntentType.COMMAND_START: {
            "keywords": ["启动", "开始", "开工", "运行", "开机"],
            "weight": 0.7,
        },
        IntentType.COMMAND_STOP: {
            "keywords": ["停止", "关掉", "暂停", "停工", "关机", "紧急停止"],
            "weight": 0.8,
        },
        IntentType.COMMAND_EVACUATE: {
            "keywords": ["疏散", "撤离", "逃生", "撤退", "撤", "快撤", "紧急撤离"],
            "weight": 0.95,
        },
        IntentType.STATUS_QUERY: {
            "keywords": ["怎么样", "状态", "情况", "查询", "看看", "检查", "正常吗"],
            "weight": 0.5,
        },
    }

    # 否定词（降低置信度）
    NEGATIVE_WORDS = ["没有", "不是", "不", "别", "未"]

    def __init__(self):
        self.config = self.KEYWORD_CONFIG

    def detect(self, text: str) -> IntentResult:
        """
        检测文本意图
        
        Args:
            text: 输入文本
            
        Returns:
            IntentResult 对象
        """
        text_lower = text.lower()
        matched_intents = []
        
        for intent_type, config in self.config.items():
            keywords = config["keywords"]
            matched_kw = []
            
            for kw in keywords:
                if kw in text:
                    matched_kw.append(kw)
            
            if matched_kw:
                # 计算基础置信度
                base_confidence = config["weight"]
                
                # 根据匹配关键词数量调整
                match_ratio = len(matched_kw) / len(keywords)
                confidence = min(base_confidence + match_ratio * 0.1, 1.0)
                
                # 检查否定词
                has_negative = any(neg in text for neg in self.NEGATIVE_WORDS)
                if has_negative:
                    confidence *= 0.3
                
                matched_intents.append({
                    "intent": intent_type,
                    "confidence": confidence,
                    "keywords_matched": matched_kw,
                })
        
        if not matched_intents:
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities={},
                raw_text=text,
                keywords_matched=[],
            )
        
        # 选择最高置信度的意图
        best = max(matched_intents, key=lambda x: x["confidence"])
        
        return IntentResult(
            intent=best["intent"],
            confidence=best["confidence"],
            entities=self._extract_entities(text),
            raw_text=text,
            keywords_matched=best["keywords_matched"],
        )

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """
        提取实体信息
        
        Args:
            text: 输入文本
            
        Returns:
            实体字典
        """
        entities = {}
        
        # 提取位置（简单规则）
        location_patterns = [
            r"([\u4e00-\u9fa5]{1,10}区)",
            r"([\u4e00-\u9fa5]{1,10}号)",
            r"在([\u4e00-\u9fa5]{1,5})",
        ]
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                entities["location"] = match.group(1)
                break
        
        # 提取数字（可能有数量信息）
        number_match = re.search(r"\d+", text)
        if number_match:
            entities["number"] = int(number_match.group())
        
        return entities


# 全局检测器实例
_detector: Optional[KeywordIntentDetector] = None


def get_detector() -> KeywordIntentDetector:
    """获取全局意图检测器"""
    global _detector
    if _detector is None:
        _detector = KeywordIntentDetector()
    return _detector


def detect_intent(text: str) -> IntentResult:
    """便捷函数：检测意图"""
    return get_detector().detect(text)

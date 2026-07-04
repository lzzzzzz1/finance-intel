from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


DISCLAIMER = "本工具仅用于信息整理与学习，不构成投资建议；请结合公告原文、风险承受能力和专业意见独立判断。"


POSITIVE_TERMS = ["增长", "盈利", "中标", "回购", "增持", "突破", "批准", "上调", "beat", "growth", "profit"]
NEGATIVE_TERMS = ["亏损", "减值", "处罚", "调查", "下滑", "终止", "违约", "风险", "miss", "loss", "probe"]
RISK_TERMS = ["监管", "处罚", "调查", "退市", "诉讼", "违约", "减值", "暂停", "uncertain", "risk"]
IMPORTANT_TERMS = ["年报", "季报", "业绩", "财报", "重大", "监管", "利率", "通胀", "并购", "filing", "earnings"]


@dataclass
class AnalysisResult:
    summary: str
    novice_explanation: str
    importance_score: int
    sentiment_score: int
    risk_score: int
    confidence_score: int
    key_numbers: list[str]
    caveats: list[str]
    model: str
    disclaimer: str = DISCLAIMER

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "novice_explanation": self.novice_explanation,
            "importance_score": self.importance_score,
            "sentiment_score": self.sentiment_score,
            "risk_score": self.risk_score,
            "confidence_score": self.confidence_score,
            "key_numbers": self.key_numbers,
            "caveats": self.caveats,
            "model": self.model,
            "disclaimer": self.disclaimer,
        }


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def rule_based_analysis(event: dict[str, Any]) -> AnalysisResult:
    title = event.get("title", "")
    body = event.get("body", "")
    text = f"{title} {body}".lower()
    positive = sum(1 for term in POSITIVE_TERMS if term.lower() in text)
    negative = sum(1 for term in NEGATIVE_TERMS if term.lower() in text)
    risk_hits = sum(1 for term in RISK_TERMS if term.lower() in text)
    important_hits = sum(1 for term in IMPORTANT_TERMS if term.lower() in text)

    importance = clamp(45 + important_hits * 10 + min(len(body), 4000) // 500, 0, 100)
    sentiment = clamp((positive - negative) * 18, -100, 100)
    risk = clamp(25 + risk_hits * 18 + max(0, negative - positive) * 8, 0, 100)
    confidence = 82 if event.get("trust_level", "official") == "official" else 62
    key_numbers = re.findall(r"(?:\d+(?:\.\d+)?%|\d+(?:\.\d+)?亿元|\d+(?:\.\d+)?万股|\d+(?:\.\d+)?亿美元)", body)[:8]

    summary = title if len(title) <= 120 else title[:117] + "..."
    explanation = (
        "这条信息来自可信公开来源。当前规则分析认为，它可能影响相关公司或板块的预期，"
        "需要重点核对原文中的业务变化、财务数字、监管表述和后续公告。"
    )
    caveats = ["规则分析无法替代人工阅读原文。", "评分只表示信息重要性和风险提示，不代表股价预测。"]

    return AnalysisResult(summary, explanation, importance, sentiment, risk, confidence, key_numbers, caveats, "rules-v1")


def analyze_with_openai(event: dict[str, Any], api_key: str, model: str) -> AnalysisResult:
    if not api_key:
        return rule_based_analysis(event)
    try:
        from openai import OpenAI
    except ImportError:
        return rule_based_analysis(event)

    client = OpenAI(api_key=api_key)
    prompt = {
        "task": "请基于给定财经事件做中文摘要和新手友好的量化分析。必须只依据输入事实，不得给买卖建议。",
        "required_json_fields": [
            "summary",
            "novice_explanation",
            "importance_score",
            "sentiment_score",
            "risk_score",
            "confidence_score",
            "key_numbers",
            "caveats",
        ],
        "event": {
            "title": event.get("title"),
            "source_name": event.get("source_name"),
            "source_url": event.get("source_url"),
            "published_at": event.get("published_at"),
            "category": event.get("category"),
            "body": event.get("body", "")[:8000],
        },
    }
    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": "你是谨慎的财经信息整理助手，只输出严格 JSON，不提供投资建议。"},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            text={"format": {"type": "json_object"}},
        )
        data = json.loads(response.output_text)
        return AnalysisResult(
            summary=str(data.get("summary", event.get("title", "")))[:500],
            novice_explanation=str(data.get("novice_explanation", ""))[:1200],
            importance_score=clamp(int(data.get("importance_score", 50)), 0, 100),
            sentiment_score=clamp(int(data.get("sentiment_score", 0)), -100, 100),
            risk_score=clamp(int(data.get("risk_score", 35)), 0, 100),
            confidence_score=clamp(int(data.get("confidence_score", 75)), 0, 100),
            key_numbers=[str(item) for item in data.get("key_numbers", [])][:10],
            caveats=[str(item) for item in data.get("caveats", [])][:8],
            model=model,
        )
    except Exception:
        return rule_based_analysis(event)

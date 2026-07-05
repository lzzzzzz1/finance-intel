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
NUMBER_PATTERN = re.compile(r"(?:\d+(?:\.\d+)?%|\d+(?:\.\d+)?亿元|\d+(?:\.\d+)?万股|\d+(?:\.\d+)?亿美元)")
SENTENCE_PATTERN = re.compile(r"[^。！？!?；;\n]{18,220}[。！？!?；;]?")


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


def extract_key_numbers(text: str) -> list[str]:
    numbers = []
    for match in NUMBER_PATTERN.finditer(text):
        start = max(0, match.start() - 28)
        end = min(len(text), match.end() + 32)
        context = re.sub(r"\s+", " ", text[start:end]).strip(" ，。；;：:")
        value = match.group(0)
        numbers.append(f"{value}｜{context}")
        if len(numbers) >= 8:
            break
    return numbers


def split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    sentences = [match.group(0).strip() for match in SENTENCE_PATTERN.finditer(normalized)]
    if sentences:
        return sentences[:80]
    return [normalized[:220]] if normalized else []


def build_reading_sections(text: str, max_sections: int = 5) -> list[dict[str, str]]:
    sentences = split_sentences(text)
    sections = []
    labels = ["核心内容", "背景与口径", "关键变化", "风险线索", "后续观察"]
    for index in range(0, min(len(sentences), max_sections * 3), 3):
        content = "".join(sentences[index:index + 3]).strip()
        if content:
            sections.append({"title": labels[len(sections)] if len(sections) < len(labels) else "补充信息", "content": content})
        if len(sections) >= max_sections:
            break
    return sections


def extract_evidence_snippets(text: str, title: str = "", key_numbers: list[str] | None = None, limit: int = 4) -> list[str]:
    sentences = split_sentences(text)
    number_values = [item.split("｜", 1)[0] for item in key_numbers or []]
    terms = [term for term in IMPORTANT_TERMS + RISK_TERMS if term.lower() in f"{title} {text}".lower()]
    scored = []
    for index, sentence in enumerate(sentences):
        score = 0
        score += sum(3 for value in number_values if value and value in sentence)
        score += sum(2 for term in terms if term.lower() in sentence.lower())
        score += 1 if len(sentence) > 50 else 0
        if score:
            scored.append((score, index, sentence))
    if not scored:
        scored = [(1, index, sentence) for index, sentence in enumerate(sentences[:limit])]
    scored.sort(key=lambda item: (-item[0], item[1]))
    snippets = []
    for _, _, sentence in scored:
        if sentence not in snippets:
            snippets.append(sentence)
        if len(snippets) >= limit:
            break
    return snippets


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
    key_numbers = extract_key_numbers(body)

    body_preview = re.sub(r"\s+", " ", body).strip()
    summary_parts = [title.strip()]
    if body_preview and body_preview not in title:
        summary_parts.append(body_preview[:220])
    summary = "。".join(part.strip(" 。") for part in summary_parts if part).strip()
    if len(summary) > 360:
        summary = summary[:357] + "..."
    explanation = (
        f"发生了什么：{title or '官方来源发布了一条新的财经/政策信息'}。\n"
        "为什么重要：它可能改变市场对相关公司、行业或宏观政策的预期，尤其要看是否涉及业绩、监管、融资、订单、利率或风险事件。\n"
        "还缺什么信息：需要回到官网原文核对完整口径，并继续观察后续公告、管理层解释、同板块公司反应和市场是否已经提前消化。"
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
        "task": (
            "请基于给定财经事件做中文摘要和新手友好的量化分析。必须只依据输入事实，不得给买卖建议。"
            "摘要要比标题更具体，说明发生了什么、涉及谁、核心数字或政策口径是什么。"
        ),
        "style_requirements": {
            "summary": "120-260字，使用中文自然段，尽量包含主体、事件、数字、影响范围和不确定性。",
            "novice_explanation": "用三段输出，分别以“发生了什么：”“为什么重要：”“还缺什么信息：”开头。",
            "key_numbers": "数组，每项格式为“数字｜它在原文里的含义或上下文”，不要只给裸数字。",
            "caveats": "列出需要核对的原文口径、一次性因素、滞后数据或不确定性。",
        },
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

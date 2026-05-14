"""
AI 解析层 - 将自然语言输入转换为结构化数据
新增：ai_parse_to_data() 直接输出 ParsedData，不经过文本中转
"""

import os
import json
from typing import Dict, Any, List
from ..config import get_config_value
from ..models import (
    ParsedData,
    CoverData,
    SectionData,
    ContentListData,
    ContentDetailData,
    TimelineData,
    TimelineEvent,
    ListItem,
    Page,
    PAGE_TYPE_SECTION,
    PAGE_TYPE_CONTENT_LIST,
    PAGE_TYPE_CONTENT_DETAIL,
    PAGE_TYPE_TIMELINE,
)

SYSTEM_PROMPT = """你是一个PPT内容结构化助手。
将用户输入的任意格式文本，提取并转换为标准JSON结构。

输出必须是合法的JSON，结构如下：
{
  "meta": {
    "title": "主标题",
    "subtitle": "副标题（可选）",
    "author": "汇报人/作者",
    "advisor": "导师/指导（可选）",
    "direction": "方向/主题（可选）",
    "date": "日期（可选）"
  },
  "sections": [
    {
      "title": "章节标题",
      "type": "list|detail|timeline",
      "items": ["条目1", "条目2"],
      "points": ["要点1", "要点2"],
      "events": [{"date": "时间", "title": "事件", "description": "描述"}]
    }
  ]
}

规则：
1. type=list：列举型内容（经历、获奖、技能）
2. type=detail：详细说明型（研究内容、项目介绍）
3. type=timeline：时间线内容（时间轴、计划）
4. 只返回JSON，不要任何解释
"""


def _call_ai(prompt: str) -> str:
    import urllib.request

    anthropic_api_key = get_config_value("ANTHROPIC_API_KEY")
    openai_api_key = get_config_value("OPENAI_API_KEY")
    api_key = anthropic_api_key or openai_api_key
    if not api_key:
        raise ValueError("未配置 AI API Key")
    if anthropic_api_key:
        payload = json.dumps(
            {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 4096,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
    else:
        payload = json.dumps(
            {
                "model": "gpt-4o",
                "max_tokens": 4096,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
    with urllib.request.urlopen(req) as resp:
        r = json.loads(resp.read())
        return (
            r["content"][0]["text"]
            if "content" in r
            else r["choices"][0]["message"]["content"]
        )


def ai_parse(user_input: str) -> Dict[str, Any]:
    """AI 解析：返回结构化字典（原有接口，保持向后兼容）"""
    prompt = f"请将以下内容转换为PPT结构化JSON，只返回JSON：\n\n{user_input}"
    response = _call_ai(prompt).strip()
    if "```" in response:
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    return json.loads(response)


def ai_parse_to_data(user_input: str) -> ParsedData:
    """
    AI 解析：直接输出 ParsedData 对象，不经过文本中转。
    解决 ai_parser → dict → text → TextParser 链路中信息丢失的问题。

    用法：
        parsed_data = ai_parse_to_data(user_input)
        pages = SmartPaginator().paginate(parsed_data)
        PPTXGenerator().generate(pages, "output.pptx")
    """

    result = ai_parse(user_input)
    parsed = ParsedData()

    # 元数据
    meta = result.get("meta", {})
    parsed.meta = CoverData(
        title=meta.get("title", ""),
        subtitle=meta.get("subtitle", ""),
        author=meta.get("author", ""),
        advisor=meta.get("advisor", ""),
        direction=meta.get("direction", ""),
        date=meta.get("date", ""),
    )

    # 章节
    for i, sec in enumerate(result.get("sections", []), 1):
        sec_title = sec.get("title", f"章节{i}")
        sec_type = sec.get("type", "list")

        # 章节分隔页
        parsed.sections.append(
            Page(
                page_type=PAGE_TYPE_SECTION,
                data=SectionData(part_num=str(i), part_title=sec_title),
            )
        )

        # 内容页：根据 type 构建对应数据模型
        if sec_type == "timeline":
            events = []
            for evt in sec.get("events", []):
                events.append(
                    TimelineEvent(
                        date=evt.get("date", ""),
                        title=evt.get("title", "")[:20],
                        description=evt.get("description", evt.get("title", "")),
                    )
                )
            if events:
                data = TimelineData(title=sec_title, part_num=str(i), events=events)
                parsed.sections.append(Page(page_type=PAGE_TYPE_TIMELINE, data=data))
            else:
                # 无事件降级为列表页
                items = [
                    ListItem(text=t)
                    for t in sec.get("items", sec.get("points", ["（无内容）"]))
                ]
                data = ContentListData(title=sec_title, part_num=str(i), items=items)
                parsed.sections.append(
                    Page(page_type=PAGE_TYPE_CONTENT_LIST, data=data)
                )

        elif sec_type == "detail":
            points = sec.get("points", sec.get("items", []))
            if points:
                data = ContentDetailData(
                    title=sec_title, part_num=str(i), points=points, results=[]
                )
                parsed.sections.append(
                    Page(page_type=PAGE_TYPE_CONTENT_DETAIL, data=data)
                )
            else:
                # 无要点降级为列表页
                data = ContentListData(title=sec_title, part_num=str(i), items=[])
                parsed.sections.append(
                    Page(page_type=PAGE_TYPE_CONTENT_LIST, data=data)
                )

        else:  # list 或其他
            items_raw = sec.get("items", sec.get("points", []))
            items = [
                ListItem(text=t) if isinstance(t, str) else ListItem(text=str(t))
                for t in items_raw
            ]
            data = ContentListData(
                title=sec_title,
                subtitle=parsed.meta.author,
                part_num=str(i),
                items=items,
            )
            parsed.sections.append(Page(page_type=PAGE_TYPE_CONTENT_LIST, data=data))

    return parsed

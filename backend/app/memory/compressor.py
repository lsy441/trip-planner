"""消息压缩/上下文管理 - Token截断 + 摘要压缩"""

import json
from typing import List, Optional
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)

from ..agents.agents import create_llm


class MessageCompressor:
    """消息压缩器 - 保留ToolMessage,截断早期对话,摘要压缩"""

    def __init__(self, max_recent_messages: int = 10, max_token_estimate: int = 8000):
        self.max_recent_messages = max_recent_messages
        self.max_token_estimate = max_token_estimate

    def compress(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        if len(messages) <= self.max_recent_messages:
            return messages

        print(f"  🗜️ [压缩] 原始消息数: {len(messages)}")

        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]

        non_system = [m for m in messages if not isinstance(m, SystemMessage)]
        recent = non_system[-self.max_recent_messages:]
        older = non_system[: -self.max_recent_messages]

        older_non_tool = [m for m in older if not isinstance(m, ToolMessage)]

        if older_non_tool:
            summary = self._summarize(older_non_tool)
            summary_msg = SystemMessage(content=f"[早期对话摘要]\n{summary}")
            system_messages.append(summary_msg)

        result = system_messages + tool_messages + recent

        print(f"  🗜️ [压缩] 压缩后: {len(result)} 条 (摘要{len(older_non_tool)}条)")
        return result

    def _summarize(self, messages: List[BaseMessage]) -> str:
        content_parts = []
        for msg in messages[-6:]:
            role = "用户" if isinstance(msg, HumanMessage) else "AI"
            text = msg.content[:200] if isinstance(msg.content, str) else str(msg.content)[:200]
            content_parts.append(f"{role}: {text}")

        combined = "\n".join(content_parts)

        if len(combined) < 500:
            return combined

        try:
            llm = create_llm()
            response = llm.invoke([
                SystemMessage(content="请将以下对话历史压缩为简洁摘要,保留关键信息(城市、日期、偏好、决策)。"),
                HumanMessage(content=combined),
            ])
            return response.content
        except Exception as e:
            print(f"  ⚠️ [压缩] LLM摘要失败,使用截断: {e}")
            return combined[:500] + "..."

    def estimate_tokens(self, messages: List[BaseMessage]) -> int:
        total = 0
        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            total += len(content) // 2
        return total

    def smart_compress(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        token_est = self.estimate_tokens(messages)
        if token_est <= self.max_token_estimate:
            return messages

        print(f"  🗜️ [智能压缩] Token估算: {token_est} > {self.max_token_estimate}")

        compressed = self.compress(messages)
        if self.estimate_tokens(compressed) <= self.max_token_estimate:
            return compressed

        tool_msgs = [m for m in compressed if isinstance(m, ToolMessage)]
        other_msgs = [m for m in compressed if not isinstance(m, ToolMessage)]

        while self.estimate_tokens(other_msgs) > self.max_token_estimate // 2 and len(other_msgs) > 4:
            other_msgs = other_msgs[2:]

        return other_msgs + tool_msgs


_compressor: Optional[MessageCompressor] = None


def get_compressor() -> MessageCompressor:
    global _compressor
    if _compressor is None:
        _compressor = MessageCompressor()
    return _compressor

"""ReAct Agent - Thought → Action → Observation 循环 + 景点多轮推理搜索"""

import json
import re
import functools
from typing import List, Optional, Dict, Any

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from .agents import create_llm
from .tools import search_attractions


REACT_SYSTEM_PROMPT = """你是一个使用ReAct推理模式的智能Agent。

## ReAct循环格式
你必须严格按照以下格式思考和行动:

Thought: [分析当前状态，决定下一步行动]
Action: [工具名称]
Action Input: [JSON格式参数]

Observation: [工具返回结果]

... (可重复Thought/Action/Observation)

Thought: [分析所有观察结果，得出最终结论]
Final Answer: [最终答案]

## 可用工具
{tools_description}

## 重要规则
1. 每次只能调用一个工具
2. Action Input必须是合法的JSON
3. 最多进行{max_iterations}轮循环
4. 当你认为已经获得足够信息时，输出Final Answer
5. 绝对禁止编造数据，必须使用工具获取真实信息
"""


class ReActAgent:
    """ReAct Agent - Thought-Action-Observation循环"""

    def __init__(
        self,
        tools: List[BaseTool],
        system_prompt: str = "",
        max_iterations: int = 5,
        verbose: bool = True,
    ):
        self.tools = {tool.name: tool for tool in tools}
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.llm = create_llm()
        self.tools_description = self._format_tools_description()

    def _format_tools_description(self) -> str:
        desc_parts = []
        for name, tool in self.tools.items():
            desc = f"- {name}: {tool.description}"
            desc_parts.append(desc)
        return "\n".join(desc_parts)

    def run(self, input_text: str) -> str:
        from ..services.observability import get_metrics_collector
        metrics = get_metrics_collector()
        metrics.increment("react_agent_runs")

        print(f"\n{'='*50}")
        print(f"🧠 [ReAct Agent] 开始推理循环")
        print(f"{'='*50}")

        system_content = self.system_prompt + "\n\n" + REACT_SYSTEM_PROMPT.format(
            tools_description=self.tools_description,
            max_iterations=self.max_iterations,
        )

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=input_text),
        ]

        for iteration in range(self.max_iterations):
            print(f"\n--- 🔄 第 {iteration + 1}/{self.max_iterations} 轮 ---")

            response = self.llm.invoke(messages)
            response_text = response.content
            messages.append(AIMessage(content=response_text))

            if self.verbose:
                print(f"🧠 [Thought] {response_text[:200]}...")

            final_answer = self._extract_final_answer(response_text)
            if final_answer:
                print(f"✅ [ReAct] 循环完成,共 {iteration + 1} 轮")
                metrics.increment("react_agent_successes")
                return final_answer

            action, action_input = self._extract_action(response_text)
            if action and action in self.tools:
                print(f"🔧 [Action] {action}({json.dumps(action_input, ensure_ascii=False)[:80]}...)")
                observation = self._execute_tool(action, action_input)
                print(f"👁️ [Observation] {observation[:100]}...")
                messages.append(HumanMessage(content=f"Observation: {observation}"))
            else:
                if action:
                    print(f"⚠️ [ReAct] 未知工具: {action}, 尝试继续")
                    messages.append(
                        HumanMessage(content=f"Observation: 工具 '{action}' 不存在,请使用可用工具列表中的工具。")
                    )
                else:
                    print(f"⚠️ [ReAct] 无法解析行动,尝试继续")
                    messages.append(
                        HumanMessage(content="Observation: 请按ReAct格式输出,包含Thought和Action。")
                    )

        print(f"⚠️ [ReAct] 达到最大迭代次数 {self.max_iterations}")
        metrics.increment("react_agent_max_iterations")
        fallback_response = self.llm.invoke(messages)
        return fallback_response.content

    def _extract_action(self, text: str) -> tuple:
        action_match = re.search(r"Action:\s*(\w+)", text)
        input_match = re.search(r"Action Input:\s*([\s\S]*?)(?=\n\n|\nObservation|\nThought|\nFinal|$)", text)

        if not action_match:
            return None, {}

        action_name = action_match.group(1).strip()
        action_input = {}

        if input_match:
            input_str = input_match.group(1).strip()
            try:
                action_input = json.loads(input_str)
            except json.JSONDecodeError:
                for pattern in [r'city["\s:]+([^",\s}]+)', r'keywords["\s:]+([^",\s}]+)']:
                    m = re.search(pattern, input_str)
                    if m:
                        if "city" not in action_input:
                            action_input["city"] = m.group(1)

        return action_name, action_input

    def _extract_final_answer(self, text: str) -> Optional[str]:
        match = re.search(r"Final Answer:\s*([\s\S]*?)$", text)
        if match:
            return match.group(1).strip()
        return None

    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        tool = self.tools.get(tool_name)
        if not tool:
            return f"错误: 工具 '{tool_name}' 不存在"

        try:
            result = tool.invoke(arguments)
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            error_msg = f"工具执行错误: {str(e)}"
            print(f"  ❌ [ReAct] {error_msg}")
            return error_msg


ATTRACTION_REACT_PROMPT = """你是景点搜索专家,需要使用ReAct推理模式为用户找到最合适的景点。

你的策略:
1. 先用宽泛关键词搜索(如"景点"),获取概览
2. 分析结果,判断是否需要更精确的搜索
3. 如果用户有特定偏好(如"历史文化"、"自然风光"),用该偏好作为关键词再次搜索
4. 综合多轮搜索结果,给出最终推荐

注意: 每次搜索可能返回不同类型的景点,你需要综合分析后给出最佳推荐。"""


def search_attractions_with_react(city: str, preferences: List[str] = None) -> str:
    """使用ReAct多轮推理搜索景点,失败时降级到直接搜索

    Args:
        city: 目标城市
        preferences: 用户偏好列表,如["历史文化", "自然风光"]

    Returns:
        JSON格式的景点推荐结果
    """
    from ..services.observability import get_metrics_collector, timer

    metrics = get_metrics_collector()

    try:
        agent = ReActAgent(
            tools=[search_attractions],
            system_prompt=ATTRACTION_REACT_PROMPT,
            max_iterations=3,
            verbose=True,
        )

        pref_str = "、".join(preferences) if preferences else "热门景点"
        query = f"请搜索{city}的{pref_str}景点,如果结果不够丰富,尝试用不同关键词再次搜索。"

        result = agent.run(query)

        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict) and "attractions" in parsed:
                return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            pass

        fallback_data = {
            "success": True,
            "city": city,
            "source": "react_agent",
            "attractions": [],
            "react_summary": result,
        }
        return json.dumps(fallback_data, ensure_ascii=False)

    except Exception as e:
        print(f"⚠️ [ReAct景点搜索] 推理失败,降级到直接搜索: {e}")
        metrics.increment("react_agent_fallbacks")
        return search_attractions.invoke({"city": city, "keywords": "、".join(preferences) if preferences else "景点"})

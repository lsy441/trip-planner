"""MCP客户端管理器 - 支持SSE/HTTP/STDIO多传输协议"""

import json
import asyncio
from typing import Any, Optional, Dict, List

from ..config import get_settings
from .cache import get_mcp_cache


class MCPClientManager:
    """MCP客户端管理器 - 统一管理MCP工具调用"""

    def __init__(self):
        self._sessions: Dict[str, Any] = {}
        self._tools: Dict[str, Any] = {}
        self._initialized = False
        self._use_mcp = False
        self._fallback_mode = True

    async def initialize(self):
        if self._initialized:
            return

        self._initialized = True

        asyncio.create_task(self._async_initialize())

    async def _async_initialize(self):
        print("\n" + "=" * 60)
        print("🔌 [MCP] 初始化MCP客户端管理器...")
        print("=" * 60)
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            settings = get_settings()
            api_key = settings.amap_api_key

            server_params = StdioServerParameters(
                command="uvx",
                args=["amap-mcp-server"],
                env={"AMAP_MAPS_API_KEY": api_key},
            )

            print("  📡 [MCP] 尝试连接高德MCP服务器 (STDIO)...")
            try:
                read_stream, write_stream = await asyncio.wait_for(
                    stdio_client(server_params).__anext__(), timeout=15
                )
                session = ClientSession(read_stream, write_stream)
                await asyncio.wait_for(session.initialize(), timeout=10)

                tools_result = await session.list_tools()
                for tool in tools_result.tools:
                    self._tools[tool.name] = tool
                    print(f"  ✅ [MCP] 发现工具: {tool.name}")

                self._sessions["amap"] = session
                self._use_mcp = True
                self._fallback_mode = False
                print(f"  🎉 [MCP] 连接成功! 共发现 {len(self._tools)} 个工具")

            except (asyncio.TimeoutError, Exception) as e:
                print(f"  ⚠️ [MCP] MCP服务器连接失败: {e}")
                print(f"  🔄 [MCP] 自动降级为直接API调用模式")
                self._fallback_mode = True

        except ImportError as e:
            print(f"  ⚠️ [MCP] MCP库未安装: {e}")
            print(f"  🔄 [MCP] 使用直接API调用模式")
            self._fallback_mode = True

        mode = "MCP协议" if self._use_mcp else "直接API(降级)"
        print(f"  📋 [MCP] 运行模式: {mode}")
        print("=" * 60 + "\n")

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        if not self._initialized:
            await self.initialize()

        cache = get_mcp_cache()
        cached = cache.get_with_rag(tool_name, arguments)
        if cached:
            return cached

        if self._use_mcp and not self._fallback_mode:
            try:
                result = await self._call_mcp_tool(tool_name, arguments)
                cache.set(tool_name, arguments, result)
                return result
            except Exception as e:
                print(f"  ⚠️ [MCP] 工具调用失败,降级到API: {e}")
                self._fallback_mode = True

        result = await self._call_fallback_api(tool_name, arguments)
        cache.set(tool_name, arguments, result)
        return result

    async def _call_mcp_tool(self, tool_name: str, arguments: dict) -> str:
        session = self._sessions.get("amap")
        if not session:
            raise RuntimeError("MCP会话未初始化")

        print(f"  🔧 [MCP] 调用工具: {tool_name}({json.dumps(arguments, ensure_ascii=False)[:80]}...)")
        result = await session.call_tool(tool_name, arguments)

        if result.content:
            text_parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    text_parts.append(item.text)
            return "\n".join(text_parts)
        return json.dumps({"success": False, "error": "MCP返回空结果"}, ensure_ascii=False)

    async def _call_fallback_api(self, tool_name: str, arguments: dict) -> str:
        print(f"  🌐 [API] 直接调用: {tool_name}({json.dumps(arguments, ensure_ascii=False)[:80]}...)")
        import requests as req

        settings = get_settings()
        api_key = settings.amap_api_key

        tool_map = {
            "amap_maps_text_search": self._api_text_search,
            "amap_maps_weather": self._api_weather,
            "amap_maps_geo": self._api_geo,
            "amap_maps_direction_transit_integrated_by_address": self._api_direction,
            "search_attractions": self._api_text_search,
            "search_weather": self._api_weather,
            "search_hotels": self._api_text_search,
            "search_transportation": self._api_text_search,
            "search_food": self._api_text_search,
            "get_city_map_info": self._api_geo,
        }

        handler = tool_map.get(tool_name)
        if handler:
            return handler(arguments, api_key)

        return json.dumps({"success": False, "error": f"未知工具: {tool_name}"}, ensure_ascii=False)

    def _api_text_search(self, args: dict, api_key: str) -> str:
        url = "https://restapi.amap.com/v3/place/text"
        params = {
            "key": api_key,
            "keywords": args.get("keywords", "景点"),
            "city": args.get("city", ""),
            "types": args.get("types", ""),
            "output": "json",
            "offset": args.get("offset", 10),
            "extensions": args.get("extensions", "base"),
        }
        params = {k: v for k, v in params.items() if v}
        try:
            resp = req.get(url, params=params, timeout=15)
            data = resp.json()
            if data.get("status") == "1":
                return json.dumps({"success": True, "data": data}, ensure_ascii=False)
            return json.dumps({"success": False, "error": data.get("info", "搜索失败")}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    def _api_weather(self, args: dict, api_key: str) -> str:
        url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "key": api_key,
            "city": args.get("city", ""),
            "extensions": args.get("extensions", "all"),
            "output": "json",
        }
        try:
            resp = req.get(url, params=params, timeout=15)
            data = resp.json()
            if data.get("status") == "1":
                return json.dumps({"success": True, "data": data}, ensure_ascii=False)
            return json.dumps({"success": False, "error": data.get("info", "查询失败")}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    def _api_geo(self, args: dict, api_key: str) -> str:
        url = "https://restapi.amap.com/v3/geocode/geo"
        params = {
            "key": api_key,
            "address": args.get("address", args.get("city", "")),
            "output": "json",
        }
        try:
            resp = req.get(url, params=params, timeout=15)
            data = resp.json()
            if data.get("status") == "1":
                return json.dumps({"success": True, "data": data}, ensure_ascii=False)
            return json.dumps({"success": False, "error": "未找到城市信息"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    def _api_direction(self, args: dict, api_key: str) -> str:
        url = "https://restapi.amap.com/v3/direction/transit/integrated"
        params = {
            "key": api_key,
            "origin": args.get("origin", ""),
            "destination": args.get("destination", ""),
            "city": args.get("city", ""),
            "output": "json",
        }
        try:
            resp = req.get(url, params=params, timeout=15)
            data = resp.json()
            return json.dumps({"success": True, "data": data}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    async def list_tools(self) -> List[dict]:
        if not self._initialized:
            await self.initialize()
        if self._use_mcp and self._tools:
            return [
                {"name": t.name, "description": t.description, "schema": t.inputSchema}
                for t in self._tools.values()
            ]
        return [
            {"name": "amap_maps_text_search", "description": "高德POI搜索"},
            {"name": "amap_maps_weather", "description": "高德天气查询"},
            {"name": "amap_maps_geo", "description": "高德地理编码"},
            {"name": "amap_maps_direction_transit_integrated_by_address", "description": "高德公交路线规划"},
        ]

    async def close(self):
        for name, session in self._sessions.items():
            try:
                await session.close()
            except:
                pass
        self._sessions.clear()
        self._tools.clear()
        self._initialized = False
        print("  🔌 [MCP] 所有连接已关闭")


_manager: Optional[MCPClientManager] = None


def get_mcp_manager() -> MCPClientManager:
    global _manager
    if _manager is None:
        _manager = MCPClientManager()
    return _manager

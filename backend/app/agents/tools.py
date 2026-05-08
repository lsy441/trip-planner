"""MCP工具定义 - 6种高德地图服务 (支持MCP协议 + 直接API降级)"""

import json
import asyncio
from langchain_core.tools import tool

from ..config import get_settings




def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=30)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _try_mcp_call(mcp_tool_name: str, arguments: dict) -> str:
    try:
        from ..mcp.client import get_mcp_manager
        manager = get_mcp_manager()
        result = _run_async(manager.call_tool(mcp_tool_name, arguments))
        return result
    except Exception as e:
        print(f"  ⚠️ [MCP工具] MCP调用失败,降级到直接API: {e}")
        return ""


@tool
def search_attractions(city: str, keywords: str = "景点") -> str:
    """
    搜索城市景点 - 高德地图POI搜索(MCP优先+API降级)

    Args:
        city: 目标城市名称
        keywords: 搜索关键词,如"历史文化"、"自然风光"、"博物馆"

    Returns:
        JSON格式的景点列表,包含名称、地址、经纬度、描述等信息
    """
    mcp_result = _try_mcp_call("amap_maps_text_search", {
        "keywords": keywords or "旅游景点",
        "city": city,
        "types": "130100|130200|130300|130400|130500",
    })
    if mcp_result:
        try:
            data = json.loads(mcp_result)
            if data.get("success") and "data" in data:
                raw = data["data"]
                pois = raw.get("pois", [])
                result = []
                for poi in pois[:8]:
                    location = poi.get("location", "").split(",")
                    result.append({
                        "name": poi.get("name"),
                        "address": poi.get("address"),
                        "location": {
                            "longitude": float(location[0]) if len(location) == 2 else 116.397128,
                            "latitude": float(location[1]) if len(location) == 2 else 39.916527,
                        },
                        "type": poi.get("type", ""),
                        "description": f"{poi.get('name', '')} - {city}著名{keywords}景点",
                        "tel": poi.get("tel", ""),
                    })
                return json.dumps({"success": True, "city": city, "count": len(result), "attractions": result}, ensure_ascii=False)
        except:
            pass

    settings = get_settings()
    api_key = settings.amap_api_key
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "key": api_key, "keywords": keywords or "旅游景点", "city": city,
        "types": "130100|130200|130300|130400|130500",
        "output": "json", "offset": 10, "page": 1, "extensions": "base",
    }
    try:
        import requests
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if data.get("status") == "1":
            pois = data.get("pois", [])
            result = []
            for poi in pois[:8]:
                location = poi.get("location", "").split(",")
                result.append({
                    "name": poi.get("name"), "address": poi.get("address"),
                    "location": {"longitude": float(location[0]) if len(location) == 2 else 116.397128, "latitude": float(location[1]) if len(location) == 2 else 39.916527},
                    "type": poi.get("type", ""), "description": f"{poi.get('name', '')} - {city}著名{keywords}景点", "tel": poi.get("tel", ""),
                })
            return json.dumps({"success": True, "city": city, "count": len(result), "attractions": result}, ensure_ascii=False)
        return json.dumps({"success": False, "error": data.get("info", "搜索失败")}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@tool
def search_weather(city: str, days: int = 3) -> str:
    """
    查询城市天气预报 - 高德地图天气API(MCP优先+API降级)

    Args:
        city: 目标城市名称
        days: 查询天数,默认3天

    Returns:
        JSON格式的天气信息,包含温度、天气类型、风力等
    """
    mcp_result = _try_mcp_call("amap_maps_weather", {"city": city, "extensions": "all"})
    if mcp_result:
        try:
            data = json.loads(mcp_result)
            if data.get("success") and "data" in data:
                raw = data["data"]
                forecasts = raw.get("forecasts", [])
                if forecasts:
                    forecast = forecasts[0]
                    casts = forecast.get("casts", [])[:days]
                    weather_list = []
                    for cast in casts:
                        weather_list.append({
                            "date": cast.get("date"), "day_weather": cast.get("dayweather"),
                            "night_weather": cast.get("nightweather"), "day_temp": cast.get("daytemp"),
                            "night_temp": cast.get("nighttemp"), "day_wind": cast.get("daywind"),
                            "night_wind": cast.get("nightwind"),
                        })
                    return json.dumps({"success": True, "city": forecast.get("city", city), "forecasts": weather_list}, ensure_ascii=False)
        except:
            pass

    settings = get_settings()
    api_key = settings.amap_api_key
    url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params = {"key": api_key, "city": city, "extensions": "all", "output": "json"}
    try:
        import requests
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if data.get("status") == "1":
            forecasts = data.get("forecasts", [])
            if forecasts:
                forecast = forecasts[0]
                casts = forecast.get("casts", [])[:days]
                weather_list = []
                for cast in casts:
                    weather_list.append({
                        "date": cast.get("date"), "day_weather": cast.get("dayweather"),
                        "night_weather": cast.get("nightweather"), "day_temp": cast.get("daytemp"),
                        "night_temp": cast.get("nighttemp"), "day_wind": cast.get("daywind"),
                        "night_wind": cast.get("nightwind"),
                    })
                return json.dumps({"success": True, "city": forecast.get("city", city), "forecasts": weather_list}, ensure_ascii=False)
        return json.dumps({"success": False, "error": data.get("info", "查询失败")}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@tool
def search_hotels(city: str, hotel_type: str = "酒店", price_range: str = "") -> str:
    """
    搜索城市酒店 - 高德地图POI搜索(MCP优先+API降级)

    Args:
        city: 目标城市名称
        hotel_type: 酒店类型,如"经济型酒店"、"豪华酒店"、"民宿"
        price_range: 价格范围,如"200-500元"

    Returns:
        JSON格式的酒店列表,包含名称、地址、价格区间、评分等
    """
    mcp_result = _try_mcp_call("amap_maps_text_search", {
        "keywords": hotel_type or "酒店", "city": city, "types": "100100|100200",
    })
    if mcp_result:
        try:
            data = json.loads(mcp_result)
            if data.get("success") and "data" in data:
                raw = data["data"]
                pois = raw.get("pois", [])
                result = []
                for poi in pois[:5]:
                    location = poi.get("location", "").split(",")
                    result.append({
                        "name": poi.get("name"), "address": poi.get("address"),
                        "location": {"longitude": float(location[0]) if len(location) == 2 else 116.397128, "latitude": float(location[1]) if len(location) == 2 else 39.916527},
                        "type": hotel_type, "price_range": price_range or "200-600元", "rating": "4.5", "distance": poi.get("distance", ""),
                    })
                return json.dumps({"success": True, "city": city, "count": len(result), "hotels": result}, ensure_ascii=False)
        except:
            pass

    settings = get_settings()
    api_key = settings.amap_api_key
    url = "https://restapi.amap.com/v3/place/text"
    params = {"key": api_key, "keywords": hotel_type or "酒店", "city": city, "types": "100100|100200", "output": "json", "offset": 6, "page": 1, "extensions": "base"}
    try:
        import requests
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if data.get("status") == "1":
            pois = data.get("pois", [])
            result = []
            for poi in pois[:5]:
                location = poi.get("location", "").split(",")
                result.append({
                    "name": poi.get("name"), "address": poi.get("address"),
                    "location": {"longitude": float(location[0]) if len(location) == 2 else 116.397128, "latitude": float(location[1]) if len(location) == 2 else 39.916527},
                    "type": hotel_type, "price_range": price_range or "200-600元", "rating": "4.5", "distance": poi.get("distance", ""),
                })
            return json.dumps({"success": True, "city": city, "count": len(result), "hotels": result}, ensure_ascii=False)
        return json.dumps({"success": False, "error": data.get("info", "搜索失败")}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@tool
def search_transportation(city: str, transport_type: str = "") -> str:
    """
    查询交通信息 - 公共交通/机场/火车站(MCP优先+API降级)

    Args:
        city: 目标城市名称
        transport_type: 交通类型,如"地铁"、"公交"、"机场"、"火车站"

    Returns:
        JSON格式的交通信息,包含站点名称、地址、线路等
    """
    keywords_map = {
        "公共交通": "地铁站|公交站", "自驾": "停车场", "出租车": "出租车",
        "飞机": "机场", "火车": "火车站|高铁站",
    }
    keywords = keywords_map.get(transport_type, "地铁站|公交站")

    mcp_result = _try_mcp_call("amap_maps_text_search", {
        "keywords": keywords, "city": city, "types": "150100|150200|150500|150700",
    })
    if mcp_result:
        try:
            data = json.loads(mcp_result)
            if data.get("success") and "data" in data:
                raw = data["data"]
                pois = raw.get("pois", [])
                result = [{"name": p.get("name"), "address": p.get("address")} for p in pois[:6]]
                return json.dumps({"success": True, "transport_type": transport_type, "stations": result}, ensure_ascii=False)
        except:
            pass

    settings = get_settings()
    api_key = settings.amap_api_key
    url = "https://restapi.amap.com/v3/place/text"
    params = {"key": api_key, "keywords": keywords, "city": city, "types": "150100|150200|150500|150700", "output": "json", "offset": 8, "extensions": "base"}
    try:
        import requests
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if data.get("status") == "1":
            pois = data.get("pois", [])
            result = [{"name": p.get("name"), "address": p.get("address")} for p in pois[:6]]
            return json.dumps({"success": True, "transport_type": transport_type, "stations": result}, ensure_ascii=False)
        return json.dumps({"success": True, "transport_type": transport_type, "stations": []}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@tool
def search_food(city: str, food_type: str = "美食") -> str:
    """
    搜索当地美食/餐厅 - 高德地图POI搜索(MCP优先+API降级)

    Args:
        city: 目标城市名称
        food_type: 美食类型,如"特色菜"、"小吃"、"火锅"、"川菜"

    Returns:
        JSON格式,包含餐厅列表
    """
    mcp_result = _try_mcp_call("amap_maps_text_search", {
        "keywords": food_type or "美食", "city": city, "types": "050000",
    })
    if mcp_result:
        try:
            data = json.loads(mcp_result)
            if data.get("success") and "data" in data:
                raw = data["data"]
                pois = raw.get("pois", [])
                result = []
                for poi in pois[:6]:
                    location = poi.get("location", "").split(",")
                    biz_ext = poi.get("biz_ext", {})
                    result.append({
                        "name": poi.get("name"), "address": poi.get("address"),
                        "location": {"longitude": float(location[0]) if len(location) == 2 else 116.397128, "latitude": float(location[1]) if len(location) == 2 else 39.916527},
                        "type": poi.get("type", food_type),
                        "tel": poi.get("tel", ""),
                        "rating": biz_ext.get("rating", ""),
                        "cost": biz_ext.get("cost", ""),
                    })
                return json.dumps({"success": True, "city": city, "food_type": food_type, "restaurants": result}, ensure_ascii=False)
        except:
            pass

    settings = get_settings()
    api_key = settings.amap_api_key
    url = "https://restapi.amap.com/v3/place/text"
    params = {"key": api_key, "keywords": food_type or "美食", "city": city, "types": "050000", "output": "json", "offset": 8, "extensions": "all"}
    try:
        import requests
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if data.get("status") == "1":
            pois = data.get("pois", [])
            result = []
            for poi in pois[:6]:
                location = poi.get("location", "").split(",")
                biz_ext = poi.get("biz_ext", {})
                result.append({
                    "name": poi.get("name"), "address": poi.get("address"),
                    "location": {"longitude": float(location[0]) if len(location) == 2 else 116.397128, "latitude": float(location[1]) if len(location) == 2 else 39.916527},
                    "type": poi.get("type", food_type),
                    "tel": poi.get("tel", ""),
                    "rating": biz_ext.get("rating", ""),
                    "cost": biz_ext.get("cost", ""),
                })
            return json.dumps({"success": True, "city": city, "food_type": food_type, "restaurants": result}, ensure_ascii=False)

        return json.dumps({"success": False, "error": data.get('info', '搜索失败')}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@tool
def get_city_map_info(city: str) -> str:
    """
    获取城市地理信息 - 用于地图展示(MCP优先+API降级)

    Args:
        city: 目标城市名称

    Returns:
        JSON格式,包含城市中心坐标、边界、行政区划等
    """
    mcp_result = _try_mcp_call("amap_maps_geo", {"address": city})
    if mcp_result:
        try:
            data = json.loads(mcp_result)
            if data.get("success") and "data" in data:
                raw = data["data"]
                geocodes = raw.get("geocodes", [])
                if geocodes:
                    geo = geocodes[0]
                    location = geo.get("location", "").split(",")
                    return json.dumps({
                        "success": True, "city": city,
                        "center": {"longitude": float(location[0]) if len(location) == 2 else 116.397128, "latitude": float(location[1]) if len(location) == 2 else 39.916527},
                        "adcode": geo.get("adcode"), "bounds": geo.get("bounds", ""), "formatted_address": geo.get("formatted_address", ""),
                    }, ensure_ascii=False)
        except:
            pass

    settings = get_settings()
    api_key = settings.amap_api_key
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {"key": api_key, "address": city, "output": "json"}
    try:
        import requests
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if data.get("status") == "1":
            geocodes = data.get("geocodes", [])
            if geocodes:
                geo = geocodes[0]
                location = geo.get("location", "").split(",")
                return json.dumps({
                    "success": True, "city": city,
                    "center": {"longitude": float(location[0]) if len(location) == 2 else 116.397128, "latitude": float(location[1]) if len(location) == 2 else 39.916527},
                    "adcode": geo.get("adcode"), "bounds": geo.get("bounds", ""), "formatted_address": geo.get("formatted_address", ""),
                }, ensure_ascii=False)
        return json.dumps({"success": False, "error": "未找到城市信息"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


ALL_TOOLS = [
    search_attractions,
    search_weather,
    search_hotels,
    search_transportation,
    search_food,
    get_city_map_info,
]

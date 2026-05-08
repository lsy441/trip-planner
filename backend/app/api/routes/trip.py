"""旅行规划API路由 - LangChain + LangGraph v2.1 (SSE流式)"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import json
import asyncio

from ...models.schemas import (
    TripRequest,
    TripPlanResponse
)

router = APIRouter(prefix="/trip", tags=["旅行规划"])

# 延迟导入以避免启动时初始化
def _get_planner():
    from ...agents.trip_planner_langgraph import get_langgraph_trip_planner
    return get_langgraph_trip_planner()


class FeedbackRequest(BaseModel):
    """用户反馈请求"""
    original_request: TripRequest = Field(..., description="原始旅行请求")
    feedback: str = Field(..., description="用户反馈内容")
    target: Optional[str] = Field(default="整体", description="调整目标,如'第2天','酒店','餐饮'")


@router.post(
    "/plan-stream",
    summary="生成旅行计划(流式)",
    description="SSE流式返回生成进度和最终结果"
)
async def plan_trip_stream(request: TripRequest):
    """SSE流式生成旅行计划"""
    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'start', 'message': '开始规划...'}, ensure_ascii=False)}\n\n"
            
            planner = _get_planner()
            
            async for progress in planner.plan_trip_stream(request):
                yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)
            
            yield f"data: {json.dumps({'type': 'complete', 'message': '规划完成'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post(
    "/plan",
    response_model=TripPlanResponse,
    summary="生成旅行计划",
    description="""
    根据用户输入的旅行需求,生成详细的旅行计划
    
    **工作流架构 (LangGraph v2.0):**
    - Plan阶段: 父Agent分析需求,生成任务计划
    - Execute阶段: 6个子Agent并行/串行执行(景点/天气/酒店/交通/美食/地图)
    - Replan阶段: 整合结果,智能检错,生成最终计划
    
    **核心特性:**
    - RoC推理模式: 思维→观察→行动
    - 智能缓存: 基于RAG的历史结果复用
    - 反馈调整: 增量优化,避免全量重生成
    """
)
async def plan_trip(request: TripRequest):
    """生成旅行计划"""
    try:
        print(f"\n{'='*60}")
        print(f"🚀 收到旅行规划请求:")
        print(f"   城市: {request.city}")
        print(f"   日期: {request.start_date} - {request.end_date}")
        print(f"   天数: {request.travel_days}")
        print(f"{'='*60}\n")

        planner = _get_planner()

        trip_plan = planner.plan_trip(request)

        return TripPlanResponse(
            success=True,
            message="旅行计划生成成功",
            data=trip_plan
        )

    except Exception as e:
        print(f"❌ 生成旅行计划失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"生成旅行计划失败: {str(e)}"
        )


@router.post(
    "/feedback",
    response_model=TripPlanResponse,
    summary="基于反馈调整计划",
    description="""
    基于用户反馈增量调整旅行计划
    
    **功能特点:**
    - 只调整用户指定的部分
    - 其他未提及部分保持不变
    - 避免全量重新生成,提升效率
    
    **使用示例:**
    - target="第2天", feedback="景点太多,减少到2个"
    - target="酒店", feedback="换一家更便宜的"
    - target="餐饮", feedback="增加当地特色小吃推荐"
    """
)
async def update_with_feedback(feedback_req: FeedbackRequest):
    """基于反馈更新旅行计划"""
    try:
        planner = _get_planner()
        
        trip_plan = planner.update_with_feedback(
            original_request=feedback_req.original_request,
            feedback=feedback_req.feedback,
            target=feedback_req.target
        )
        
        return TripPlanResponse(
            success=True,
            message="根据反馈调整完成",
            data=trip_plan
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"调整失败: {str(e)}"
        )


@router.get(
    "/health",
    summary="健康检查",
    description="检查旅行规划服务是否正常,返回工作流架构信息"
)
async def health_check():
    """健康检查 - 返回LangGraph工作流信息"""
    try:
        planner = _get_planner()
        
        return {
            "status": "healthy",
            "service": "trip-planner-v2.0",
            "framework": "LangChain 1.2 + LangGraph 1.1",
            "architecture": {
                "pattern": "Plan-Execute-Replan",
                "parent_agent": "父Agent(总调度)",
                "child_agents": [
                    "景点搜索专家",
                    "天气查询专家", 
                    "酒店推荐专家",
                    "交通出行专家",
                    "美食推荐专家",
                    "地图信息专家"
                ],
                "tools_count": 6,
                "features": [
                    "RoC推理模式",
                    "智能缓存(RAG复用)",
                    "反馈增量优化",
                    "上下文管理"
                ]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"服务不可用: {str(e)}"
        )

"""FastAPI主应用"""

import sys
import io

# Windows 下强制 UTF-8 输出，Emoji 完美显示 ✅
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import get_settings, validate_config, print_config
from .routes import trip, poi, chat
from ..services.observability import get_metrics_collector, logger

# 获取配置
settings = get_settings()

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于langchain框架的智能旅行规划助手API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(trip.router, prefix="/api")
app.include_router(poi.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    print("\n" + "="*60)
    print(f"[START] {settings.app_name} v{settings.app_version}")
    print("="*60)
    
    # 打印配置信息
    print_config()
    
    # 验证配置
    try:
        validate_config()
        print("\n[OK] 配置验证通过")
    except ValueError as e:
        print(f"\n[ERROR] 配置验证失败:\n{e}")
        print("\n请检查.env文件并确保所有必要的配置项都已设置")
        raise
    
    print("\n" + "="*60)
    print("API文档: http://localhost:8000/docs")
    print("ReDoc文档: http://localhost:8000/redoc")
    print("="*60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    print("\n" + "="*60)
    print("[STOP] 应用正在关闭...")
    print("="*60 + "\n")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


@app.get("/metrics")
async def metrics():
    """系统指标 - 计数器、耗时统计、缓存状态"""
    metrics_collector = get_metrics_collector()
    summary = metrics_collector.get_summary()

    try:
        from ..mcp.cache import get_mcp_cache
        cache = get_mcp_cache()
        summary["cache"] = cache.stats()
    except Exception:
        pass

    return summary


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )


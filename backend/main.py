"""
魅丽健康助手 - 后端服务入口

FastAPI 应用主入口，配置路由、中间件和 CORS
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from config import get_settings
from api import auth, user, ai

# 创建 FastAPI 应用
app = FastAPI(
    title="魅丽健康助手 API",
    description="提供用户认证、AI 试穿、中医分析等服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(ai.router, prefix="/api")


@app.get("/")
async def root():
    """健康检查端点"""
    return {
        "status": "ok",
        "message": "魅丽健康助手后端服务正在运行",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """健康检查端点（用于部署监控）"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )

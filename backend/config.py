"""
配置管理模块

从环境变量中读取所有配置项，确保敏感信息不被硬编码
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # Supabase 配置
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    
    # Gemini API 配置
    gemini_api_key: str = ""
    
    # 应用配置
    debug: bool = False
    cors_origins: list[str] = [
        "http://localhost:5173", "http://localhost:3000", "http://localhost:3001",
        "http://127.0.0.1:5173", "http://127.0.0.1:3000", "http://127.0.0.1:3001"
    ]
    # 支付宝配置
    alipay_app_id: str = ""
    alipay_app_private_key: str = ""
    alipay_public_key: str = ""
    alipay_sign_type: str = "RSA2"
    alipay_debug: bool = True  # 沙箱模式默认为 True
    alipay_notify_url: str = ""
    alipay_return_url: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例
    
    使用 lru_cache 确保配置只加载一次
    """
    return Settings()

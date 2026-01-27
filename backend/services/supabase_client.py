"""
Supabase 客户端模块

提供 Supabase 客户端的初始化和管理
"""
from supabase import create_client, Client
from config import get_settings


def get_supabase_client() -> Client:
    """
    获取 Supabase 客户端实例
    
    使用 service_role_key 以便后端拥有完整权限
    """
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key
    )


def get_supabase_anon_client() -> Client:
    """
    获取匿名权限的 Supabase 客户端
    
    用于前端认证场景的模拟
    """
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key
    )

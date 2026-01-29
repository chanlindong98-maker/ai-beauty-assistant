"""
配置服务模块

提供从数据库动态加载配置的功能，并支持环境变量回退
"""
import logging
from functools import lru_cache
from typing import Any, Dict
from config import get_settings
from services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class ConfigService:
    _config_cache: Dict[str, str] = {}
    _last_fetch_time = 0

    @classmethod
    def clear_cache(cls):
        """清除配置缓存，确保下次获取时从数据库读取最新值"""
        cls._config_cache = {}

    @classmethod
    def get_all_config(cls, force_refresh: bool = False) -> Dict[str, str]:
        """
        获取所有动态配置项
        """
        # 简单缓存逻辑，实际生产环境可增加 TTL
        if not cls._config_cache or force_refresh:
            try:
                supabase = get_supabase_client()
                res = supabase.table("system_config").select("key", "value").execute()
                if res.data:
                    cls._config_cache = {item["key"]: item["value"] for item in res.data}
                else:
                    cls._config_cache = {}
            except Exception as e:
                logger.error(f"Failed to fetch system config: {str(e)}")
                # 如果数据库查询失败，确保返回空字典而不是报错
                return {}
        return cls._config_cache

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        获取特定配置项，数据库优先，环境变量次之
        """
        # 1. 尝试从动态配置（缓存）中获取
        configs = cls.get_all_config()
        if key in configs:
            return configs[key]

        # 2. 尝试从 Settings (环境变量) 中获取
        settings = get_settings()
        if hasattr(settings, key):
            return getattr(settings, key)

        return default

def get_config(key: str, default: Any = None) -> Any:
    """快捷获取配置的函数"""
    return ConfigService.get(key, default)

def clear_config_cache():
    """清除配置缓存"""
    ConfigService.clear_cache()

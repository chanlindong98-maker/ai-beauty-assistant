"""
管理后台相关的请求/响应模型
"""
from pydantic import BaseModel, Field
from datetime import datetime

class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    total_users: int
    total_recharge_amount: float
    today_recharge_amount: float
    total_orders: int
    active_users_24h: int

class SystemConfigItem(BaseModel):
    """系统配置项"""
    key: str
    value: str
    description: str | None = None

class UpdateUserCreditsRequest(BaseModel):
    """更新用户额度请求"""
    user_id: str
    credits: int
    mode: str = Field("set", description="set: 设置为该值, add: 在当前基础上增加")

class UserDetail(BaseModel):
    """管理端看到的用户详情"""
    id: str
    nickname: str
    email: str | None
    credits: int
    is_admin: bool
    created_at: str | None = None
    last_login: str | None = None

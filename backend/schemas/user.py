"""
用户相关的请求/响应模型
"""
from pydantic import BaseModel, Field


class UpdateCreditsRequest(BaseModel):
    """更新魔法值请求"""
    delta: int = Field(..., description="变化量，正数增加，负数减少")


class ProcessReferralRequest(BaseModel):
    """处理推荐奖励请求"""
    new_user_device_id: str = Field(..., description="新用户的设备 ID")


class RedeemRequest(BaseModel):
    """兑换码兑换请求"""
    code: str = Field(..., description="兑换码")


class UserResponse(BaseModel):
    """用户响应"""
    success: bool
    message: str
    data: dict | None = None

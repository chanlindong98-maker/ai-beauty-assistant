"""
认证相关的请求/响应模型
"""
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, description="密码")
    nickname: str = Field(..., min_length=1, max_length=50, description="昵称")
    device_id: str = Field(..., description="设备 ID (由客户端生成)")
    referrer_id: str | None = Field(None, description="推荐人设备 ID")


class LoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class AuthResponse(BaseModel):
    """认证响应"""
    success: bool
    message: str
    user: dict | None = None
    access_token: str | None = None


class UserProfile(BaseModel):
    """用户资料"""
    id: str
    username: str
    nickname: str
    device_id: str
    credits: int
    referrals_today: int
    last_referral_date: str
    is_admin: bool = False

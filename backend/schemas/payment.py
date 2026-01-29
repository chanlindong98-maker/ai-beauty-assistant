"""
支付相关的请求/响应模型
"""
from pydantic import BaseModel, Field

class CreateOrderRequest(BaseModel):
    """创建支付订单请求"""
    amount: float = Field(..., description="支付金额")
    credits: int = Field(..., description="充值的次数")

class CreateOrderResponse(BaseModel):
    """创建支付订单响应"""
    success: bool
    message: str
    pay_url: str | None = None
    order_id: str | None = None

class AlipayNotifyResponse(BaseModel):
    """接口响应标识"""
    status: str

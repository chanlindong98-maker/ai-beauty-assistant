"""
支付宝服务模块

封装支付宝 SDK，提供支付创建、验签等功能
支持从数据库动态读取配置
"""
import logging
from alipay import AliPay
from config import get_settings
from services.supabase_client import get_supabase_client

from services.config_service import get_config

logger = logging.getLogger(__name__)

def get_alipay_client() -> AliPay:
    """
    获取支付宝客户端实例
    """
    # 优先从数据库动态配置获取，否则从环境变量获取
    app_id = get_config("alipay_app_id")
    private_key = get_config("alipay_app_private_key")
    public_key = get_config("alipay_public_key")
    sign_type = get_config("alipay_sign_type")
    
    debug_val = get_config("alipay_debug")
    # 兼容字符串或布尔值
    if isinstance(debug_val, str):
        debug = debug_val.lower() == "true"
    else:
        debug = bool(debug_val)
        
    notify_url = get_config("alipay_notify_url")

    # 支付宝 SDK 初始化
    alipay = AliPay(
        appid=app_id,
        app_notify_url=notify_url,
        app_private_key_string=private_key,
        alipay_public_key_string=public_key,
        sign_type=sign_type,
        debug=debug
    )
    return alipay

def create_alipay_order(out_trade_no: str, total_amount: float, subject: str, return_url: str = None):
    """
    创建支付订单 URL
    """
    alipay = get_alipay_client()
    
    ret_url = return_url or get_config("alipay_return_url")
    not_url = get_config("alipay_notify_url")
    
    debug_val = get_config("alipay_debug")
    if isinstance(debug_val, str):
        debug = debug_val.lower() == "true"
    else:
        debug = bool(debug_val)

    order_string = alipay.api_alipay_trade_page_pay(
        out_trade_no=out_trade_no,
        total_amount=total_amount,
        subject=subject,
        return_url=ret_url,
        notify_url=not_url
    )
    
    # 生成支付链接
    if debug:
        gateway = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
    else:
        gateway = "https://openapi.alipay.com/gateway.do"
        
    return f"{gateway}?{order_string}"

def verify_alipay_data(data: dict, signature: str) -> bool:
    """
    验证支付宝异步通知参数及签名
    """
    alipay = get_alipay_client()
    return alipay.verify(data, signature)

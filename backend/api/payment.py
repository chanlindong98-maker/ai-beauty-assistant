"""
支付相关 API 端点

处理支付宝订单创建和异步回调
"""
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from schemas.payment import CreateOrderRequest, CreateOrderResponse
from middleware.auth import get_current_user
from services.supabase_client import get_supabase_client
from services.alipay_service import create_alipay_order, verify_alipay_data

router = APIRouter(prefix="/payment", tags=["支付"])
logger = logging.getLogger(__name__)

@router.post("/alipay/create", response_model=CreateOrderResponse)
async def create_payment_order(
    request: CreateOrderRequest,
    current_user: dict = Depends(get_current_user)
) -> CreateOrderResponse:
    """
    创建支付宝支付订单
    """
    # 1. 生成唯一商户订单号
    out_trade_no = f"PAY_{uuid.uuid4().hex[:16]}"
    
    # 2. 这里的金额和次数应该在后端有固定的套餐校验，暂时简单处理
    # 实际应用中应：if request.amount not in PRICING_PLANS: raise ...
    
    # 3. 将订单写入数据库 (Supabase)
    supabase = get_supabase_client()
    try:
        order_data = {
            "out_trade_no": out_trade_no,
            "user_id": current_user["id"],
            "amount": request.amount,
            "credits_to_add": request.credits,
            "status": "PENDING"
        }
        
        result = supabase.table("orders").insert(order_data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="订单创建失败")
            
        # 4. 调用支付宝服务生成支付链接
        subject = f"能量充值 - {request.credits}次"
        pay_url = create_alipay_order(
            out_trade_no=out_trade_no,
            total_amount=request.amount,
            subject=subject
        )
        
        return CreateOrderResponse(
            success=True,
            message="订单已创建",
            pay_url=pay_url,
            order_id=out_trade_no
        )
        
    except Exception as e:
        logger.error(f"Create order error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务繁忙: {str(e)}")

@router.post("/alipay/notify")
async def alipay_notify(request: Request):
    """
    接收支付宝异步通知
    """
    # 1. 获取通知参数
    body = await request.body()
    # 支付宝发送的是 application/x-www-form-urlencoded
    from urllib.parse import parse_qs
    params = parse_qs(body.decode("utf-8"))
    # parse_qs 返回的是字典，值是列表，需要转换
    data = {k: v[0] for k, v in params.items()}
    
    # 2. 提取签名并验签
    signature = data.pop("sign", None)
    if not signature:
        return "failure"
        
    if not verify_alipay_data(data, signature):
        logger.warning(f"Alipay signature verification failed for order: {data.get('out_trade_no')}")
        return "failure"
    
    # 3. 校验订单状态
    trade_status = data.get("trade_status")
    if trade_status not in ["TRADE_SUCCESS", "TRADE_FINISHED"]:
        return "success" # 支付宝要求非成功也返回 success 以停止重试，或者根据业务决定
        
    out_trade_no = data.get("out_trade_no")
    alipay_trade_no = data.get("trade_no")
    
    # 4. 业务逻辑处理：更新订单状态并给用户充值
    supabase = get_supabase_client()
    try:
        # 查询订单
        order_res = supabase.table("orders").select("*").eq("out_trade_no", out_trade_no).execute()
        if not order_res.data:
            return "failure"
            
        order = order_res.data[0]
        if order["status"] == "PAID":
            return "success" # 已处理过
            
        # 更新订单状态 (注意：生产环境建议放在事务中)
        supabase.table("orders").update({
            "status": "PAID",
            "alipay_trade_no": alipay_trade_no
        }).eq("out_trade_no", out_trade_no).execute()
        
        # 给用户加上 credits
        user_res = supabase.table("user_profiles").select("credits").eq("id", order["user_id"]).execute()
        if user_res.data:
            current_credits = user_res.data[0]["credits"]
            new_credits = current_credits + order["credits_to_add"]
            supabase.table("user_profiles").update({"credits": new_credits}).eq("id", order["user_id"]).execute()
            
        return "success"
        
    except Exception as e:
        logger.error(f"Alipay notify processing error: {str(e)}")
        return "failure"

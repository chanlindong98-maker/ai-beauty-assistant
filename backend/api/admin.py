"""
管理后台 API 端点

提供统计数据、用户管理和系统配置功能
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import date, datetime, timedelta
from schemas.admin import DashboardStats, SystemConfigItem, UpdateUserCreditsRequest, UserDetail
from middleware.auth import get_admin_user
from services.supabase_client import get_supabase_client

router = APIRouter(prefix="/admin", tags=["管理员后台"])

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(_: dict = Depends(get_admin_user)) -> DashboardStats:
    """
    获取后台大盘统计数据
    """
    supabase = get_supabase_client()
    
    # 1. 总用户数
    users_res = supabase.table("user_profiles").select("id", count="exact").execute()
    total_users = users_res.count or 0
    
    # 2. 充值总额和总订单数 (已支付)
    orders_res = supabase.table("orders").select("amount").eq("status", "PAID").execute()
    total_recharge_amount = sum(item["amount"] for item in orders_res.data) if orders_res.data else 0
    total_orders = len(orders_res.data) if orders_res.data else 0
    
    # 3. 今日充值额
    today = str(date.today())
    today_orders_res = supabase.table("orders")\
        .select("amount")\
        .eq("status", "PAID")\
        .gte("created_at", f"{today}T00:00:00")\
        .execute()
    today_recharge_amount = sum(item["amount"] for item in today_orders_res.data) if today_orders_res.data else 0
    
    # 4. 24小时内活跃用户 (简单用已生成的记录数模拟或查询 auth 控制台，这里简化处理)
    # 实际项目中应有专门的日志表
    active_users_24h = total_users # 暂时占位
    
    return DashboardStats(
        total_users=total_users,
        total_recharge_amount=total_recharge_amount,
        today_recharge_amount=today_recharge_amount,
        total_orders=total_orders,
        active_users_24h=active_users_24h
    )

@router.get("/users", response_model=List[UserDetail])
async def list_users(
    query: str = None, 
    _: dict = Depends(get_admin_user)
) -> List[UserDetail]:
    """
    获取会员列表
    """
    supabase = get_supabase_client()
    builder = supabase.table("user_profiles").select("*")
    
    if query:
        builder = builder.ilike("nickname", f"%{query}%")
    
    res = builder.order("id").limit(100).execute()
    
    users = []
    for item in res.data:
        users.append(UserDetail(
            id=item["id"],
            nickname=item["nickname"],
            email=None, # profile 表里没存 email
            credits=item["credits"],
            is_admin=item.get("is_admin", False)
        ))
    return users

@router.post("/users/credits")
async def update_user_credits(
    request: UpdateUserCreditsRequest,
    _: dict = Depends(get_admin_user)
):
    """
    手动修改用户使用次数
    """
    supabase = get_supabase_client()
    
    if request.mode == "add":
        # 获取当前值
        res = supabase.table("user_profiles").select("credits").eq("id", request.user_id).single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="用户不存在")
        new_credits = res.data["credits"] + request.credits
    else:
        new_credits = request.credits
        
    if new_credits < 0:
        new_credits = 0
        
    supabase.table("user_profiles")\
        .update({"credits": new_credits})\
        .eq("id", request.user_id)\
        .execute()
        
    return {"success": True, "message": f"成功更新为 {new_credits} 次", "new_credits": new_credits}

@router.get("/config", response_model=List[SystemConfigItem])
async def get_system_config(_: dict = Depends(get_admin_user)) -> List[SystemConfigItem]:
    """
    获取系统配置 (如支付参数、AI 密钥)
    
    逻辑：优先返回数据库中的值，如果某个关键 key 不存在于数据库，
    则从环境变量中读取并显示（确保管理员能看到当前实际生效的配置）
    """
    from config import get_settings
    settings = get_settings()
    
    supabase = get_supabase_client()
    res = supabase.table("system_config").select("*").execute()
    
    # 将数据库配置转为字典，方便查找
    db_config = {item["key"]: item for item in (res.data or [])}
    
    # 定义所有需要在后台显示的关键配置项及其描述
    essential_keys = [
        ("gemini_api_key", "Google Gemini API 密钥 (AI 核心)", settings.gemini_api_key),
        ("alipay_app_id", "支付宝 AppID", settings.alipay_app_id),
        ("alipay_app_private_key", "支付宝应用私钥", settings.alipay_app_private_key),
        ("alipay_public_key", "支付宝公钥", settings.alipay_public_key),
        ("alipay_notify_url", "支付宝异步回调地址", settings.alipay_notify_url),
        ("alipay_return_url", "支付宝同步跳转地址", settings.alipay_return_url),
    ]
    
    result = []
    added_keys = set()
    
    for key, desc, env_val in essential_keys:
        if key in db_config:
            # 数据库有值，使用数据库的
            result.append(SystemConfigItem(**db_config[key]))
        else:
            # 数据库没有，使用环境变量的当前值
            result.append(SystemConfigItem(key=key, value=env_val or "", description=desc))
        added_keys.add(key)
    
    # 添加数据库中存在但不在 essential_keys 中的其他配置
    for item in (res.data or []):
        if item["key"] not in added_keys:
            result.append(SystemConfigItem(**item))
    
    return result

@router.post("/config/update")
async def update_system_config(
    items: List[SystemConfigItem],
    _: dict = Depends(get_admin_user)
):
    """
    更新系统配置
    """
    from services.config_service import clear_config_cache
    
    supabase = get_supabase_client()
    for item in items:
        # 使用 upsert
        supabase.table("system_config").upsert({
            "key": item.key,
            "value": item.value,
            "description": item.description,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
    
    # 清除配置缓存，确保下次读取时获取最新值
    clear_config_cache()
        
    return {"success": True, "message": "配置已更新"}

@router.post("/reset-password")
async def reset_admin_password(
    request: dict, # {"new_password": "..."}
    admin_user: dict = Depends(get_admin_user)
):
    """
    管理员修改自身密码
    """
    new_pwd = request.get("new_password")
    if not new_pwd or len(new_pwd) < 6:
        raise HTTPException(status_code=400, detail="新密码长度至少为 6 位")
        
    supabase = get_supabase_client()
    # 使用 Admin API 修改密码
    supabase.auth.admin.update_user_by_id(
        admin_user["id"],
        {"password": new_pwd}
    )
    
    return {"success": True, "message": "密码修改成功！"}

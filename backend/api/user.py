"""
用户 API 端点

处理用户资料获取和更新操作
"""
import re
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from schemas.user import UpdateCreditsRequest, UserResponse, RedeemRequest
from middleware.auth import get_current_user
from services.supabase_client import get_supabase_client

router = APIRouter(prefix="/user", tags=["用户"])


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: dict = Depends(get_current_user)) -> UserResponse:
    """
    获取当前用户资料
    """
    return UserResponse(
        success=True,
        message="获取成功",
        data={
            "id": current_user["id"],
            "nickname": current_user["nickname"],
            "device_id": current_user["device_id"],
            "credits": current_user["credits"],
            "referrals_today": current_user["referrals_today"],
            "last_referral_date": current_user["last_referral_date"],
            "is_admin": current_user.get("is_admin", False)
        }
    )


@router.put("/credits", response_model=UserResponse)
async def update_credits(
    request: UpdateCreditsRequest,
    current_user: dict = Depends(get_current_user)
) -> UserResponse:
    """
    更新用户魔法值
    
    通常在使用功能时扣减（delta=-1），或获得奖励时增加（delta=1）
    """
    supabase = get_supabase_client()
    new_credits = current_user["credits"] + request.delta
    
    # 防止魔法值变为负数
    if new_credits < 0:
        raise HTTPException(status_code=400, detail="魔法值不足")
    
    try:
        result = supabase.table("user_profiles")\
            .update({"credits": new_credits})\
            .eq("id", current_user["id"])\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="更新失败")
        
        return UserResponse(
            success=True,
            message="魔法值已更新",
            data={"credits": new_credits}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.get("/share-link")
async def get_share_link(current_user: dict = Depends(get_current_user)) -> dict:
    """
    获取分享链接信息
    
    返回用户的设备 ID 用于生成推荐链接
    """
    return {
        "success": True,
        "device_id": current_user["device_id"],
        "referrals_today": current_user["referrals_today"],
        "max_referrals_per_day": 5
    }


@router.post("/check-referral-status")
async def check_referral_status(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    检查并更新推荐状态
    
    如果是新的一天，重置今日推荐计数
    """
    supabase = get_supabase_client()
    today = str(date.today())
    
    if current_user["last_referral_date"] != today:
        # 新的一天，重置计数
        supabase.table("user_profiles")\
            .update({
                "referrals_today": 0,
                "last_referral_date": today
            })\
            .eq("id", current_user["id"])\
            .execute()
        
        return {
            "success": True,
            "referrals_today": 0,
            "is_new_day": True
        }
    
    return {
        "success": True,
        "referrals_today": current_user["referrals_today"],
        "is_new_day": False
    }


@router.post("/redeem", response_model=UserResponse)
async def redeem_code(
    request: RedeemRequest,
    current_user: dict = Depends(get_current_user)
) -> UserResponse:
    """
    通过兑换码获得魔法次数
    
    规则：今天日期(DD) + 兑换次数 + 4个大写字母 + 13天后日期(DD) + 2个小写字母
    例如 2026-01-28 兑换 10 次：2810ABCD10xy
    """
    code = request.code.strip()
    
    # 1. 使用正则表达式解析兑换码
    # (\d{2}) - 今天日期
    # (\d+) - 兑换次数
    # ([A-Z]{4}) - 4个大写字母
    # (\d{2}) - 13天后日期
    # ([a-z]{2}) - 2个小写字母
    pattern = r"^(\d{2})(\d+)([A-Z]{4})(\d{2})([a-z]{2})$"
    match = re.match(pattern, code)
    
    if not match:
        raise HTTPException(status_code=400, detail="兑换码格式不对哦，请检查一下~")
    
    today_dd_str, credits_str, random_caps, later_dd_str, random_smalls = match.groups()
    
    # 2. 验证日期规则
    today = date.today()
    later_day = today + timedelta(days=13)
    
    expected_today_dd = today.strftime("%d")
    expected_later_dd = later_day.strftime("%d")
    
    if today_dd_str != expected_today_dd or later_dd_str != expected_later_dd:
        raise HTTPException(status_code=400, detail="哎呀，这个兑换码不是今天的，或者已经过期了。")
    
    credits_to_add = int(credits_str)
    if credits_to_add <= 0:
        raise HTTPException(status_code=400, detail="无效的魔法点数")
    
    supabase = get_supabase_client()
    
    # 3. 检查兑换码是否已被使用
    try:
        check_result = supabase.table("used_redeem_codes")\
            .select("code")\
            .eq("code", code)\
            .execute()
        
        if check_result.data and len(check_result.data) > 0:
            raise HTTPException(status_code=400, detail="这个兑换码已经用过啦，不能重复使用哦。")
            
        # 4. 插入使用记录并更新用户金币
        # 注意：此处应使用事务，但 Supabase Python SDK 事务支持较复杂，通过 Service Role 顺序操作
        
        # 记录已使用
        supabase.table("used_redeem_codes").insert({
            "code": code,
            "user_id": current_user["id"],
            "credits_added": credits_to_add
        }).execute()
        
        # 更新用户魔法值
        current_credits = current_user["credits"]
        new_credits = current_credits + credits_to_add
        
        supabase.table("user_profiles")\
            .update({"credits": new_credits})\
            .eq("id", current_user["id"])\
            .execute()
        
        return UserResponse(
            success=True,
            message=f"兑换成功！获得了 {credits_to_add} 次魔法能量 ✨",
            data={"credits": new_credits}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"兑换过程中出错了: {str(e)}")

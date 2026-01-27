"""
用户 API 端点

处理用户资料获取和更新操作
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from schemas.user import UpdateCreditsRequest, UserResponse
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
            "last_referral_date": current_user["last_referral_date"]
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

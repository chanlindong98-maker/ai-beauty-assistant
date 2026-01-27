"""
认证 API 端点

处理用户注册、登录、登出等认证相关操作
"""
import uuid
from datetime import date
from fastapi import APIRouter, HTTPException
from schemas.auth import RegisterRequest, LoginRequest, AuthResponse
from services.supabase_client import get_supabase_client

router = APIRouter(prefix="/auth", tags=["认证"])


def generate_device_id() -> str:
    """生成唯一设备 ID"""
    return uuid.uuid4().hex[:12]


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest) -> AuthResponse:
    """
    用户注册
    
    创建新用户账号，初始赠送 3 次魔法值。
    如果提供了推荐人 ID，在注册成功后处理推荐奖励。
    """
    supabase = get_supabase_client()
    
    # 使用用户名作为邮箱的一部分（Supabase Auth 需要邮箱）
    email = f"{request.username}@happy-beauty.local"
    
    try:
        # 创建 Supabase Auth 用户
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": request.password,
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="注册失败，请稍后重试")
        
        user_id = auth_response.user.id
        device_id = generate_device_id()
        
        # 创建用户资料
        profile_data = {
            "id": user_id,
            "nickname": request.nickname,
            "device_id": device_id,
            "credits": 3,
            "referrals_today": 0,
            "last_referral_date": str(date.today()),
            "referrer_id": None
        }
        
        # 处理推荐逻辑
        if request.referrer_id:
            # 查找推荐人
            referrer_result = supabase.table("user_profiles")\
                .select("*")\
                .eq("device_id", request.referrer_id)\
                .execute()
            
            if referrer_result.data and len(referrer_result.data) > 0:
                referrer = referrer_result.data[0]
                today = str(date.today())
                
                # 检查是否超过每日推荐上限
                current_referrals = referrer["referrals_today"] if referrer["last_referral_date"] == today else 0
                
                if current_referrals < 5:
                    # 更新推荐人的魔法值和推荐计数
                    supabase.table("user_profiles")\
                        .update({
                            "credits": referrer["credits"] + 1,
                            "referrals_today": current_referrals + 1,
                            "last_referral_date": today
                        })\
                        .eq("id", referrer["id"])\
                        .execute()
                    
                    profile_data["referrer_id"] = referrer["id"]
        
        # 插入用户资料
        supabase.table("user_profiles").insert(profile_data).execute()
        
        return AuthResponse(
            success=True,
            message="注册成功！赠送你 3 次魔法值。" + ("推荐人也获得了奖励！" if profile_data["referrer_id"] else ""),
            user={
                "id": user_id,
                "username": request.username,
                "nickname": request.nickname,
                "device_id": device_id,
                "credits": 3,
                "referrals_today": 0,
                "last_referral_date": str(date.today())
            },
            access_token=auth_response.session.access_token if auth_response.session else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # 检查是否是用户名重复
        if "already registered" in str(e).lower():
            raise HTTPException(status_code=400, detail="这个用户名被抢走啦，换一个吧！")
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> AuthResponse:
    """
    用户登录
    
    验证用户凭据并返回访问令牌
    """
    supabase = get_supabase_client()
    email = f"{request.username}@happy-beauty.local"
    
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": request.password,
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=401, detail="用户名或密码不对哦~")
        
        user_id = auth_response.user.id
        
        # 获取用户资料
        profile_result = supabase.table("user_profiles")\
            .select("*")\
            .eq("id", user_id)\
            .single()\
            .execute()
        
        if not profile_result.data:
            raise HTTPException(status_code=404, detail="用户资料不存在")
        
        profile = profile_result.data
        
        return AuthResponse(
            success=True,
            message="欢迎回来！",
            user={
                "id": user_id,
                "username": request.username,
                "nickname": profile["nickname"],
                "device_id": profile["device_id"],
                "credits": profile["credits"],
                "referrals_today": profile["referrals_today"],
                "last_referral_date": profile["last_referral_date"]
            },
            access_token=auth_response.session.access_token if auth_response.session else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        if "invalid" in str(e).lower():
            raise HTTPException(status_code=401, detail="用户名或密码不对哦~")
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.post("/logout", response_model=AuthResponse)
async def logout() -> AuthResponse:
    """
    用户登出
    
    NOTE: 实际的 token 失效需要在客户端处理
    """
    return AuthResponse(
        success=True,
        message="已安全登出",
        user=None,
        access_token=None
    )

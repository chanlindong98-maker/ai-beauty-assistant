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
    
    使用管理员权限创建新用户账号，初始赠送 3 次魔法值。
    如果提供了推荐人 ID，在注册成功后处理推荐奖励。
    直接标记邮箱已验证，绕过邮件确认。
    """
    supabase = get_supabase_client()
    
    # 使用用户名作为邮箱的一部分（Supabase Auth 需要邮箱）
    email = f"{request.username}@happy-beauty.app"
    
    try:
        # 1. 使用 Admin API 直接创建已验证的用户
        # 这样可以保持当前客户端的 Service Role 权限，用于后续更新推荐人资料
        admin_response = supabase.auth.admin.create_user({
            "email": email,
            "password": request.password,
            "email_confirm": True
        })
        
        if not admin_response.user:
            raise HTTPException(status_code=400, detail="注册失败，请稍后重试")
        
        user_id = admin_response.user.id
        device_id = request.device_id
        
        # 1.5 查重判定：如果设备已存在，则初始额度为 0
        device_check = supabase.table("user_profiles")\
            .select("id")\
            .eq("device_id", device_id)\
            .limit(1)\
            .execute()
        
        has_gift_already = len(device_check.data) > 0
        initial_credits = 0 if has_gift_already else 3
        
        # 创建用户资料
        profile_data = {
            "id": user_id,
            "nickname": request.nickname,
            "device_id": device_id,
            "credits": initial_credits,
            "referrals_today": 0,
            "last_referral_date": str(date.today()),
            "referrer_id": None,
            "is_admin": (request.username == "lindong")
        }
        
        # 2. 处理推荐逻辑 (由于是 Admin 权限创建，此处操作会成功)
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
        
        # 3. 插入新用户资料
        supabase.table("user_profiles").insert(profile_data).execute()
        
        # 4. 调用登录接口，获取 Session (给前端返回 Token)
        login_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": request.password,
        })
        
        msg = "注册成功！"
        if initial_credits > 0:
            msg += f"赠送你 {initial_credits} 次魔法值。"
        else:
            msg += "欢迎加入！由于该设备已领取过礼包，本次注册不再额外赠送魔法值。"
            
        if profile_data["referrer_id"]:
            msg += "推荐人获得了奖励！"

        return AuthResponse(
            success=True,
            message=msg,
            user={
                "id": user_id,
                "username": request.username,
                "nickname": request.nickname,
                "device_id": device_id,
                "credits": initial_credits,
                "referrals_today": 0,
                "last_referral_date": str(date.today()),
                "is_admin": (request.username == "lindong")
            },
            access_token=login_response.session.access_token if login_response.session else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # 检查是否是用户名重复
        err_str = str(e).lower()
        if "already registered" in err_str or "user already exists" in err_str:
            raise HTTPException(status_code=400, detail="这个用户名被抢走啦，换一个吧！")
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> AuthResponse:
    """
    用户登录
    
    验证用户凭据并返回访问令牌
    """
    supabase = get_supabase_client()
    email = f"{request.username}@happy-beauty.app"
    
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
        
        profile = profile_result.data
        
        if not profile:
            # 如果资料不存在，按需自动创建一个（防止由于注册一半失败导致无法登录）
            device_id = generate_device_id()
            profile = {
                "id": user_id,
                "nickname": request.username,
                "device_id": device_id,
                "credits": 3,
                "referrals_today": 0,
                "last_referral_date": str(date.today()),
                "is_admin": (request.username == "lindong")
            }
            supabase.table("user_profiles").insert(profile).execute()
        elif request.username == "lindong":
            # 或者是预设管理员，确保权限同步
            supabase.table("user_profiles").update({"is_admin": True}).eq("id", user_id).execute()
            profile["is_admin"] = True
        
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
                "last_referral_date": profile["last_referral_date"],
                "is_admin": profile.get("is_admin", False)
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

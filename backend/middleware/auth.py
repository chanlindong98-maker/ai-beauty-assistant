"""
认证中间件

提供 JWT 验证和用户身份提取功能
"""
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.supabase_client import get_supabase_client

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    验证 JWT token 并返回当前用户信息
    
    Args:
        credentials: HTTP Bearer 认证凭据
    
    Returns:
        用户信息字典
    
    Raises:
        HTTPException: token 无效或用户不存在
    """
    token = credentials.credentials
    supabase = get_supabase_client()
    
    try:
        # 验证 token 并获取用户
        user_response = supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="无效的认证令牌")
        
        user_id = user_response.user.id
        
        # 获取用户资料
        profile_response = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
        
        if not profile_response.data:
            raise HTTPException(status_code=404, detail="用户资料不存在")
        
        return {
            "id": user_id,
            "email": user_response.user.email,
            **profile_response.data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"认证失败: {str(e)}")


async def get_optional_user(
    request: Request
) -> dict | None:
    """
    可选的用户认证
    
    如果提供了有效的 token 则返回用户信息，否则返回 None
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    
    try:
        supabase = get_supabase_client()
        user_response = supabase.auth.get_user(token)
        
        if user_response and user_response.user:
            user_id = user_response.user.id
            profile_response = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
            
            if profile_response.data:
                return {
                    "id": user_id,
                    "email": user_response.user.email,
                    **profile_response.data
                }
    except Exception:
        pass
    
async def get_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    验证当前用户是否为管理员
    """
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
